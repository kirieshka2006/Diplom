from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend
from .models import EmailConfirmation
import logging

logger = logging.getLogger(__name__)


def send_confirmation_code(user, email):
    """Отправляет 6-значный код на email"""

    # Удаляем старые коды
    EmailConfirmation.objects.filter(user=user, confirmed_at__isnull=True).delete()

    # Создаем новый код
    confirmation = EmailConfirmation.objects.create(
        user=user,
        email=email,
    )

    # Текст письма с кодом
    subject = 'Код подтверждения email'
    message = f"""
    Здравствуйте, {user.username}!

    Ваш код подтверждения: {confirmation.code}

    Введите этот код в поле подтверждения в вашем профиле.

    Код действителен 15 минут.

    С уважением, Администратор сайта :)
    """

    # Отправляем письмо с обработкой ошибок
    try:
        # Убираем пробелы из пароля, если они есть
        password = settings.EMAIL_HOST_PASSWORD.replace(' ', '') if settings.EMAIL_HOST_PASSWORD else ''
        
        # Используем EmailMessage - Django автоматически обработает UTF-8
        email_msg = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.EMAIL_HOST_USER,
            to=[email],
        )
        # Явно устанавливаем кодировку UTF-8
        email_msg.content_subtype = 'plain'
        email_msg.encoding = 'utf-8'
        email_msg.send(fail_silently=False)
        
        logger.info(f"Код подтверждения отправлен на {email} для пользователя {user.username}")
    except Exception as e:
        logger.error(f"Ошибка отправки email на {email}: {str(e)}")
        # Пробуем альтернативный способ - через connection с правильной кодировкой
        try:
            import sys
            import io
            # Устанавливаем UTF-8 для stdout/stderr чтобы избежать проблем с кодировкой
            if sys.stdout.encoding != 'utf-8':
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            if sys.stderr.encoding != 'utf-8':
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            
            connection = EmailBackend(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=password,
                use_tls=settings.EMAIL_USE_TLS,
                use_ssl=settings.EMAIL_USE_SSL if hasattr(settings, 'EMAIL_USE_SSL') else False,
                fail_silently=False,
            )
            connection.open()
            
            email_msg = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.EMAIL_HOST_USER,
                to=[email],
                connection=connection,
            )
            email_msg.content_subtype = 'plain'
            email_msg.encoding = 'utf-8'
            email_msg.send()
            connection.close()
            logger.info(f"Код подтверждения отправлен на {email} (через явное подключение)")
        except Exception as e2:
            logger.error(f"Критическая ошибка отправки email: {str(e2)}")
            raise Exception(f"Не удалось отправить email. Проверьте настройки SMTP. Ошибка: {str(e2)}")

    return confirmation.code


def send_recovery_code(user, email):
    """Отправляет код для восстановления пароля"""
    # Удаляем старые коды восстановления
    EmailConfirmation.objects.filter(
        user=user,
        email=email,
        confirmed_at__isnull=True
    ).delete()

    # Создаем новый код восста��овления
    recovery = EmailConfirmation.objects.create(
        user=user,
        email=email,
    )

    subject = 'Код восстановления пароля'
    message = f"""
Здравствуйте, {user.username}!

Ваш код для восстановления пароля: {recovery.code}

Введите этот код в форме восстановления пароля.

Код действителен 15 минут.

Если вы не запрашивали восстановление пароля, проигнорируйте это письмо.

С уважением,
Система бронирования переговорок
"""

    # Отправляем письмо с обработкой ошибок
    try:
        # Убираем пробелы из пароля, если они есть
        password = settings.EMAIL_HOST_PASSWORD.replace(' ', '') if settings.EMAIL_HOST_PASSWORD else ''
        
        # Используем EmailMessage - Django автоматически обработает UTF-8
        email_msg = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.EMAIL_HOST_USER,
            to=[email],
        )
        email_msg.content_subtype = 'plain'
        email_msg.encoding = 'utf-8'
        email_msg.send(fail_silently=False)
        
        logger.info(f"Код восстановления отправлен на {email} для пользователя {user.username}")
    except Exception as e:
        logger.error(f"Ошибка отправки email на {email}: {str(e)}")
        # Пробуем альтернативный способ - через connection
        try:
            import sys
            import io
            # Устанавливаем UTF-8 для stdout/stderr
            if sys.stdout.encoding != 'utf-8':
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            if sys.stderr.encoding != 'utf-8':
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            
            connection = EmailBackend(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=password,
                use_tls=settings.EMAIL_USE_TLS,
                use_ssl=settings.EMAIL_USE_SSL if hasattr(settings, 'EMAIL_USE_SSL') else False,
                fail_silently=False,
            )
            connection.open()
            
            email_msg = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.EMAIL_HOST_USER,
                to=[email],
                connection=connection,
            )
            email_msg.content_subtype = 'plain'
            email_msg.encoding = 'utf-8'
            email_msg.send()
            connection.close()
            logger.info(f"Код восстановления отправлен на {email} (через явное подключение)")
        except Exception as e2:
            logger.error(f"Критическая ошибка отправки email: {str(e2)}")
            raise Exception(f"Не удалось отправить email. Проверьте настройки SMTP. Ошибка: {str(e2)}")

    return recovery.code
