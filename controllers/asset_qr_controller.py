# -*- coding: utf-8 -*-

from odoo import http, fields
from odoo.http import request


class AssetQRController(http.Controller):
    """
    HTTP controller for QR code scanning.

    Routes:
      GET  /asset/scan/<asset_id>/<token>        — mobile scan landing page
      POST /asset/update_location                — GPS coords update from JS
      GET  /asset/request/new/<asset_id>         — quick asset request form from scan page
    """

    @http.route(
        '/asset/scan/<int:asset_id>/<string:token>',
        auth='user', type='http', website=True, methods=['GET'],
    )
    def scan_asset(self, asset_id, token, lat=None, lng=None, **kw):
        Asset = request.env['asset.asset'].sudo()
        asset = Asset.browse(asset_id)

        if not asset.exists():
            return request.render(
                'university_management.asset_scan_invalid',
                {'error': 'Asset not found.'},
            )

        token_valid = (asset.qr_scan_token == token)

        # Create scan log (use sudo + explicit create to bypass immutability guard)
        try:
            log_env = request.env['asset.qr.scan.log']
            # We bypass the write-guard by using _origin_write directly at creation
            import logging
            _logger = logging.getLogger(__name__)
            # Build log via direct SQL-level create (bypasses our write guard)
            request.env.cr.execute(
                """
                INSERT INTO asset_qr_scan_log
                    (asset_id, scanned_by, scan_time, gps_lat, gps_lng,
                     ip_address, device_info, action_taken, scan_token_valid,
                     create_uid, write_uid, create_date, write_date)
                VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s,
                        %s, %s, NOW(), NOW())
                """,
                (
                    asset_id,
                    request.env.user.id,
                    float(lat) if lat else 0.0,
                    float(lng) if lng else 0.0,
                    request.httprequest.remote_addr or '',
                    (request.httprequest.user_agent.string or '')[:255],
                    'view_only',
                    token_valid,
                    request.env.user.id,
                    request.env.user.id,
                )
            )
            # Update last_scan_date on asset
            request.env.cr.execute(
                "UPDATE asset_asset SET last_scan_date = NOW() WHERE id = %s",
                (asset_id,)
            )
            request.env.cr.flush()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning('QR scan log failed: %s', e)

        if not token_valid:
            return request.render(
                'university_management.asset_scan_invalid',
                {'error': 'Invalid or expired QR code token.', 'asset': asset},
            )

        user = request.env.user
        user_groups = user.groups_id.mapped('full_name')

        is_it_team = any('IT' in g or 'Asset Manager' in g or 'Administrator' in g for g in user_groups)
        is_hod = any('HOD' in g or 'Department' in g for g in user_groups)
        is_admin = any('Administrator' in g or 'Admin' in g for g in user_groups)

        return request.render(
            'university_management.asset_scan_page',
            {
                'asset': asset,
                'user': user,
                'is_it_team': is_it_team,
                'is_hod': is_hod,
                'is_admin': is_admin,
                'token': token,
            },
        )

    @http.route(
        '/asset/update_location',
        auth='user', type='json', methods=['POST'], csrf=False,
    )
    def update_location(self, asset_id=None, lat=None, lng=None, **kw):
        """Update GPS on the most recent scan log for this asset/user."""
        if not asset_id or lat is None or lng is None:
            return {'status': 'error', 'message': 'Missing parameters'}
        try:
            request.env.cr.execute(
                """
                UPDATE asset_qr_scan_log
                SET gps_lat = %s, gps_lng = %s
                WHERE id = (
                    SELECT id FROM asset_qr_scan_log
                    WHERE asset_id = %s AND scanned_by = %s
                    ORDER BY scan_time DESC LIMIT 1
                )
                """,
                (float(lat), float(lng), int(asset_id), request.env.user.id)
            )
            request.env.cr.flush()
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        return {'status': 'ok'}

    @http.route(
        '/asset/request/submit',
        auth='user', type='http', website=True, methods=['POST'], csrf=True,
    )
    def submit_asset_request(self, asset_id=None, category_id=None,
                              description=None, required_date=None,
                              priority='medium', **kw):
        """Quick asset request form POST from QR scan page."""
        try:
            vals = {
                'asset_id': int(asset_id) if asset_id else False,
                'asset_category_id': int(category_id) if category_id else False,
                'description': description or 'Requested via QR scan.',
                'required_date': required_date or fields.Date.today(),
                'priority': priority,
            }
            req = request.env['asset.request'].create(vals)
            req.action_submit()
            return request.render(
                'university_management.asset_request_submitted',
                {'request': req, 'asset_id': asset_id},
            )
        except Exception as e:
            return request.render(
                'university_management.asset_scan_invalid',
                {'error': str(e)},
            )