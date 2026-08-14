{
    "name": "Activity Plans - Scheduled Email",
    "version": "19.0.1.1.0",
    "category": "Productivity/Discuss",
    "summary": "Turn an Activity Type into a scheduled email so an Activity Plan "
               "queues emails by date, like the chatter 'Send Later'.",
    "description": "Odoo's Activity Plans schedule several activities (to-dos) on a record at once. "
                   "An Activity Type can already carry mail templates natively, but those only give "
                   "the user manual Preview / Send Now buttons in the chatter, so nothing is ever "
                   "sent by date. This module lets you flag an Activity Type as a scheduled email. "
                   "When such a type is scheduled, typically as one line inside an Activity Plan, the "
                   "module reproduces exactly what the chatter Send Later feature does: it renders the "
                   "template through the native mail composer and stores the result as a scheduled "
                   "message with a future date. The native cron then posts it on the due date, and the "
                   "linked activity is auto-completed. No custom cron and no custom outgoing-mail "
                   "plumbing: the module only wires together native, documented extension points.",
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    # 'mail' is the only dependency: mail.activity.type, mail.activity.plan,
    # mail.compose.message, mail.scheduled.message and the cron that posts
    # scheduled messages all live in the 'mail' addon.
    "depends": ["mail"],
    "data": [
        "views/mail_activity_type_views.xml",
    ],
    # icon/banner are authored as .svg and referenced here as .png (the .png is
    # produced from the .svg before publishing), per the Ganemo branding flow.
    "icon": "/mail_activity_plan_scheduled_mail/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 139.0,
    "module_type": "official",
}
