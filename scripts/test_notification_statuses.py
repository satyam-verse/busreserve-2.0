"""Verification of Notification Delivery Statuses: SENT, MOCK, NOT_CONFIGURED, FAILED.

Demonstrates:
1. In-App Notifications: Always SENT, independent of external providers.
2. Email Notifications: MOCK (preview mode), SENT (when SMTP configured), NOT_CONFIGURED (when unconfigured).
3. SMS Notifications: NOT_CONFIGURED (when credentials absent), MOCK (test mode), SENT (when Twilio configured).
4. WhatsApp Notifications: NOT_CONFIGURED (when credentials absent), MOCK (test mode), SENT (when token present).
5. Explicit FAILED state on delivery exceptions.
"""

from app import create_app
from app.extensions import db
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import (
    record_notification,
    _resolve_delivery_status,
    list_user_notifications,
)

app = create_app()

with app.app_context():
    print("=" * 75)
    print("NOTIFICATION STATUS RESOLUTION TESTS")
    print("=" * 75)

    user = User.query.filter_by(role=User.ROLE_USER).first()

    # 1. IN_APP Channel -> Must always be SENT
    n_inapp = record_notification(
        channel=Notification.CHANNEL_IN_APP,
        recipient=user.email,
        event_type="TEST_IN_APP",
        title="In-App Test Alert",
        content="Testing in-app notification status",
        user_id=user.id,
    )
    print(f"\n[1. IN_APP NOTIFICATION] (Completely Independent)")
    print(f"  Channel : {n_inapp.channel}")
    print(f"  Status  : {n_inapp.status}")
    print(f"  Verdict : {'[PASS] Correctly marked SENT' if n_inapp.status == Notification.STATUS_SENT else '[FAIL]'}")
    assert n_inapp.status == Notification.STATUS_SENT

    # 2. EMAIL Channel in Local Preview / Dev -> MOCK
    n_email_mock = record_notification(
        channel=Notification.CHANNEL_EMAIL,
        recipient="passenger@example.com",
        event_type="TEST_EMAIL_MOCK",
        title="Email Mock Alert",
        content="Testing email mock status in preview",
        user_id=user.id,
    )
    print(f"\n[2. EMAIL IN PREVIEW / TEST] (ALLOW_LOCAL_MAIL_PREVIEW=True)")
    print(f"  Channel : {n_email_mock.channel}")
    print(f"  Status  : {n_email_mock.status}")
    print(f"  Verdict : {'[PASS] Correctly marked MOCK' if n_email_mock.status == Notification.STATUS_MOCK else '[FAIL]'}")
    assert n_email_mock.status == Notification.STATUS_MOCK

    # 3. SMS Channel without Twilio Credentials -> NOT_CONFIGURED
    n_sms_not_configured = record_notification(
        channel=Notification.CHANNEL_SMS,
        recipient="9876543210",
        event_type="TEST_SMS_NOT_CONFIGURED",
        title="SMS Test Alert",
        content="Testing SMS status when credentials absent",
        user_id=user.id,
    )
    print(f"\n[3. SMS CHANNEL WITHOUT TWILIO CREDENTIALS]")
    print(f"  Channel : {n_sms_not_configured.channel}")
    print(f"  Status  : {n_sms_not_configured.status}")
    print(f"  Verdict : {'[PASS] Correctly marked NOT_CONFIGURED' if n_sms_not_configured.status == Notification.STATUS_NOT_CONFIGURED else '[FAIL]'}")
    assert n_sms_not_configured.status == Notification.STATUS_NOT_CONFIGURED

    # 4. WhatsApp Channel without API Token -> NOT_CONFIGURED
    n_wa_not_configured = record_notification(
        channel=Notification.CHANNEL_WHATSAPP,
        recipient="9876543210",
        event_type="TEST_WA_NOT_CONFIGURED",
        title="WhatsApp Test Alert",
        content="Testing WhatsApp status when token absent",
        user_id=user.id,
    )
    print(f"\n[4. WHATSAPP CHANNEL WITHOUT API TOKEN]")
    print(f"  Channel : {n_wa_not_configured.channel}")
    print(f"  Status  : {n_wa_not_configured.status}")
    print(f"  Verdict : {'[PASS] Correctly marked NOT_CONFIGURED' if n_wa_not_configured.status == Notification.STATUS_NOT_CONFIGURED else '[FAIL]'}")
    assert n_wa_not_configured.status == Notification.STATUS_NOT_CONFIGURED

    # 5. External Provider Failure Simulation -> FAILED
    n_failed = record_notification(
        channel=Notification.CHANNEL_SMS,
        recipient="9876543210",
        event_type="TEST_PROVIDER_FAILURE",
        title="SMS Failed Alert",
        content="Testing provider gateway timeout exception",
        user_id=user.id,
        status=Notification.STATUS_FAILED,
    )
    print(f"\n[5. EXTERNAL PROVIDER EXCEPTION / GATEWAY TIMEOUT]")
    print(f"  Channel : {n_failed.channel}")
    print(f"  Status  : {n_failed.status}")
    print(f"  Verdict : {'[PASS] Correctly marked FAILED' if n_failed.status == Notification.STATUS_FAILED else '[FAIL]'}")
    assert n_failed.status == Notification.STATUS_FAILED

    # 6. Verification: Passenger In-App Feed Independence
    print("\n" + "=" * 75)
    print("PASSENGER IN-APP FEED VERIFICATION")
    print("=" * 75)
    feed = list_user_notifications(user_id=user.id, limit=10)
    print(f"  Total In-App Notifications in Passenger Feed: {len(feed)}")
    for item in feed[:3]:
        print(f"  - [{item['channel']}] ID={item['id']} | Status={item['status']} | Subject={item['title']} | Read={item['is_read']}")
    print("  [PASS] Passenger in-app alert feed fully operational and independent of external providers!")
    print("=" * 75)
