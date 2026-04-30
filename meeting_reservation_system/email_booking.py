from django.core.mail import EmailMessage
from django.utils.timezone import localtime
from django.conf import settings


def send_booking_confirmation(booking):
    """Отправка подтверждения бронирования"""

    # ★★★ ИСПОЛЬЗУЕМ ДАННЫЕ ИЗ БРОНИ, А НЕ ИЗ ПОЛЬЗОВАТЕЛЯ ★★★
    contact_name = booking.booking_full_name or booking.user.first_name or booking.user.username
    recipient_email = booking.booking_email or booking.user.email

    if not recipient_email:
        print(f"❌ Нет email для отправки письма (бронирование #{booking.id})")
        return

    room = booking.room

    start = localtime(booking.start_time)
    end = localtime(booking.end_time)

    subject = f"✅ Ваше бронирование подтверждено — {room.name}"

    # 🏢 ОФИС
    office = room.office

    if office:
        office_info = f"""
🏢 Месторасположение:
Название офиса: {office.name}
Адрес: {office.address}
Телефон: {office.phone or "не указан"}
Часы работы: {office.work_hours or "не указаны"}
Ссылка на карту: {office.yandex_map_url or "не указана"}
"""
    else:
        office_info = "🏢 Месторасположение: офис не выбран\n"

    # 📩 ОСНОВНОЕ ПИСЬМО
    message = f"""
Здравствуйте, {contact_name}!

Ваше бронирование подтверждено.

📅 Дата: {start.strftime('%d.%m.%Y')}
⏰ Время: {start.strftime('%H:%M')} — {end.strftime('%H:%M')}
⏱️ Длительность: {(booking.end_time - booking.start_time).seconds // 3600} часа

{office_info}

💰 Итоговая стоимость: {booking.total_price} руб.
"""

    if booking.manager_comment:
        message += f"📝 Комментарий менеджера:\n{booking.manager_comment}\n\n"

    message += "Если у вас возникнут вопросы — просто ответьте на это письмо."

    # Используем EmailMessage с явной UTF-8 кодировкой для поддержки русских символов
    email_msg = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.EMAIL_HOST_USER,
        to=[recipient_email],
    )
    email_msg.encoding = 'utf-8'
    email_msg.send(fail_silently=False)
    
    print(f"📧 Письмо отправлено на {recipient_email} (контакт: {contact_name})")