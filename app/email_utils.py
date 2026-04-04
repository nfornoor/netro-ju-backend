import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .config import get_settings

settings = get_settings()


async def send_email(to_email: str, subject: str, html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )


async def send_otp_email(to_email: str, full_name: str, otp: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
      <div style="background: #0f1e3c; padding: 20px; border-radius: 8px 8px 0 0;">
        <h2 style="color: #c9a227; margin: 0; text-align: center;">গাজীপুর জাহাঙ্গীরনগর</h2>
        <p style="color: #fff; text-align: center; margin: 5px 0;">Gazipur District Union - JU</p>
      </div>
      <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; border: 1px solid #e0e0e0;">
        <h3 style="color: #0f1e3c;">প্রিয় {full_name},</h3>
        <p style="color: #555;">আপনার ইমেইল যাচাই করতে নিচের কোডটি ব্যবহার করুন:</p>
        <div style="background: #0f1e3c; color: #c9a227; font-size: 32px; font-weight: bold;
                    letter-spacing: 8px; text-align: center; padding: 20px; border-radius: 8px; margin: 20px 0;">
          {otp}
        </div>
        <p style="color: #888; font-size: 13px;">এই কোডটি <strong>১০ মিনিট</strong> পর্যন্ত বৈধ।</p>
        <p style="color: #888; font-size: 13px;">যদি আপনি এই অনুরোধ না করে থাকেন, এই ইমেইলটি উপেক্ষা করুন।</p>
      </div>
    </div>
    """
    await send_email(to_email, "ইমেইল যাচাইকরণ কোড - গাজীপুর জাহাঙ্গীরনগর", html)


async def send_admin_new_user_notification(full_name: str, email: str, phone: str, batch: str, department: str):
    admin_url = f"{settings.frontend_url}/admin"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
      <div style="background: #0f1e3c; padding: 20px; border-radius: 8px 8px 0 0;">
        <h2 style="color: #c9a227; margin: 0;">নতুন সদস্য অনুরোধ</h2>
      </div>
      <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; border: 1px solid #e0e0e0;">
        <p>একটি নতুন সদস্যপদের অনুরোধ এসেছে এবং ইমেইল যাচাই সম্পন্ন হয়েছে।</p>
        <table style="width: 100%; border-collapse: collapse;">
          <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>নাম</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{full_name}</td></tr>
          <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>ইমেইল</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{email}</td></tr>
          <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>ফোন</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{phone}</td></tr>
          <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>ব্যাচ</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{batch}</td></tr>
          <tr><td style="padding: 8px;"><strong>বিভাগ</strong></td><td style="padding: 8px;">{department}</td></tr>
        </table>
        <div style="margin-top: 20px; text-align: center;">
          <a href="{admin_url}" style="background: #c9a227; color: #0f1e3c; padding: 12px 24px;
             text-decoration: none; border-radius: 6px; font-weight: bold;">অনুমোদন করুন</a>
        </div>
      </div>
    </div>
    """
    await send_email(settings.admin_email, f"নতুন সদস্য অনুরোধ: {full_name}", html)


async def send_approval_email(to_email: str, full_name: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
      <div style="background: #0f1e3c; padding: 20px; border-radius: 8px 8px 0 0;">
        <h2 style="color: #c9a227; margin: 0; text-align: center;">স্বাগতম!</h2>
        <p style="color: #fff; text-align: center;">গাজীপুর জাহাঙ্গীরনগর</p>
      </div>
      <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; border: 1px solid #e0e0e0;">
        <h3 style="color: #0f1e3c;">প্রিয় {full_name},</h3>
        <p style="color: #555;">আপনার সদস্যপদ অনুমোদিত হয়েছে। এখন আপনি আমাদের প্ল্যাটফর্মে লগইন করতে পারবেন।</p>
        <p style="color: #555;">আপনার ফোন নম্বর এবং পাসওয়ার্ড দিয়ে লগইন করুন।</p>
        <div style="margin-top: 20px; text-align: center;">
          <a href="{settings.frontend_url}" style="background: #c9a227; color: #0f1e3c; padding: 12px 24px;
             text-decoration: none; border-radius: 6px; font-weight: bold;">এখনই লগইন করুন</a>
        </div>
      </div>
    </div>
    """
    await send_email(to_email, "সদস্যপদ অনুমোদিত - গাজীপুর জাহাঙ্গীরনগর", html)


async def send_rejection_email(to_email: str, full_name: str, reason: str = ""):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
      <div style="background: #0f1e3c; padding: 20px; border-radius: 8px 8px 0 0;">
        <h2 style="color: #c9a227; margin: 0; text-align: center;">গাজীপুর জাহাঙ্গীরনগর</h2>
      </div>
      <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; border: 1px solid #e0e0e0;">
        <h3 style="color: #0f1e3c;">প্রিয় {full_name},</h3>
        <p style="color: #555;">দুঃখিত, আপনার সদস্যপদ অনুরোধ অনুমোদিত হয়নি।</p>
        {f'<p style="color: #555;"><strong>কারণ:</strong> {reason}</p>' if reason else ''}
        <p style="color: #555;">আরও তথ্যের জন্য আমাদের সাথে যোগাযোগ করুন।</p>
      </div>
    </div>
    """
    await send_email(to_email, "সদস্যপদ অনুরোধ - গাজীপুর জাহাঙ্গীরনগর", html)


async def send_notice_notification(to_emails: list[str], title: str, content: str, notice_type: str, show_donation_button: bool = False):
    type_label = "ইভেন্ট" if notice_type == "event" else "নোটিশ"
    donation_section = f"""
        <div style="margin-top: 16px; padding: 16px; background: #fff8e1; border: 1px solid #c9a227; border-radius: 8px; text-align: center;">
          <p style="color: #0f1e3c; font-weight: bold; margin: 0 0 10px;">আপনার সহযোগিতা আমাদের অনুপ্রাণিত করে</p>
          <a href="{settings.frontend_url}/donate" style="background: #c9a227; color: #0f1e3c; padding: 10px 24px;
             text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">ডোনেশন করুন</a>
        </div>
    """ if show_donation_button else ""
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
      <div style="background: #0f1e3c; padding: 20px; border-radius: 8px 8px 0 0;">
        <h2 style="color: #c9a227; margin: 0;">নতুন {type_label}</h2>
        <p style="color: #fff; margin: 5px 0;">গাজীপুর জাহাঙ্গীরনগর</p>
      </div>
      <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; border: 1px solid #e0e0e0;">
        <h3 style="color: #0f1e3c;">{title}</h3>
        <p style="color: #555; line-height: 1.6;">{content}</p>
        {donation_section}
        <div style="margin-top: 20px; text-align: center;">
          <a href="{settings.frontend_url}/#notices" style="background: #c9a227; color: #0f1e3c; padding: 12px 24px;
             text-decoration: none; border-radius: 6px; font-weight: bold;">বিস্তারিত দেখুন</a>
        </div>
      </div>
    </div>
    """
    for email in to_emails:
        try:
            await send_email(email, f"নতুন {type_label}: {title}", html)
        except Exception:
            pass  # Don't fail if one email fails
