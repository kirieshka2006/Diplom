import os
from functools import lru_cache
from pathlib import Path

from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.db.models import Max, Count
from django.utils import timezone
from .models import Room, RoomImage, User, EmailConfirmation, Booking, Office, Review, ReviewReply, Equipment, FAQ, FAQCategory, InfoBlock, InfoSection
from django.http import JsonResponse, FileResponse, Http404
from datetime import datetime, timedelta
from .models import SupportTicket, TicketResponse
import json
from decimal import Decimal
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from django.utils.text import slugify
from django.conf import settings
import pandas as pd
import io
from django.utils.timezone import localtime
from openpyxl import load_workbook
import re
from PIL import Image, ImageDraw, ImageFont
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

STATUS_CHOICES = dict(Booking.STATUS_CHOICES)

PDF_PAGE_WIDTH = 1754
PDF_PAGE_HEIGHT = 1240
PDF_PAGE_MARGIN_X = 64
PDF_PAGE_MARGIN_Y = 54
PDF_CELL_PADDING_X = 12
PDF_CELL_PADDING_Y = 10


@lru_cache(maxsize=None)
def _get_pdf_font(size, bold=False):
    font_candidates = [
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        Path('/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/dejavu/DejaVuSans.ttf'),
        Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'),
        settings.BASE_DIR / 'static' / 'fonts' / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),
    ]

    for font_path in font_candidates:
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=size)

    return ImageFont.load_default()


def _text_width(draw, text, font):
    return draw.textbbox((0, 0), text or '', font=font)[2]


def _line_height(draw, font):
    bbox = draw.textbbox((0, 0), 'Ag', font=font)
    return (bbox[3] - bbox[1]) + 4


def _split_long_word(draw, word, font, max_width):
    parts = []
    current = ''

    for char in word:
        candidate = f'{current}{char}'
        if not current or _text_width(draw, candidate, font) <= max_width:
            current = candidate
            continue

        parts.append(current)
        current = char

    if current:
        parts.append(current)

    return parts or ['']


def _wrap_pdf_text(draw, text, font, max_width):
    normalized = str(text or '—').replace('\n', ' ').strip()
    if not normalized:
        return ['—']

    lines = []
    current = ''

    for raw_word in normalized.split():
        word_parts = [raw_word]
        if _text_width(draw, raw_word, font) > max_width:
            word_parts = _split_long_word(draw, raw_word, font, max_width)

        for word in word_parts:
            candidate = word if not current else f'{current} {word}'
            if current and _text_width(draw, candidate, font) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate

    if current:
        lines.append(current)

    return lines or ['—']


def _draw_pdf_table_header(draw, headers, column_widths, x_start, y_start, header_font):
    line_height = _line_height(draw, header_font)
    row_height = line_height + (PDF_CELL_PADDING_Y * 2)
    x = x_start

    for index, header in enumerate(headers):
        width = column_widths[index]
        draw.rectangle(
            [x, y_start, x + width, y_start + row_height],
            fill='#dce9d8',
            outline='#9eaf9a',
            width=2,
        )
        draw.text(
            (x + PDF_CELL_PADDING_X, y_start + PDF_CELL_PADDING_Y),
            str(header),
            font=header_font,
            fill='#223022',
        )
        x += width

    return y_start + row_height


def _build_table_pdf(title, headers, rows, filename, column_fractions):
    title_font = _get_pdf_font(30, bold=True)
    meta_font = _get_pdf_font(16)
    header_font = _get_pdf_font(16, bold=True)
    body_font = _get_pdf_font(15)

    content_width = PDF_PAGE_WIDTH - (PDF_PAGE_MARGIN_X * 2)
    column_widths = [int(content_width * fraction) for fraction in column_fractions]
    column_widths[-1] += content_width - sum(column_widths)

    pages = []

    def start_page(page_number):
        image = Image.new('RGB', (PDF_PAGE_WIDTH, PDF_PAGE_HEIGHT), 'white')
        draw = ImageDraw.Draw(image)
        y = PDF_PAGE_MARGIN_Y

        draw.text((PDF_PAGE_MARGIN_X, y), title, font=title_font, fill='#1f2a1f')
        meta_text = f'Сформировано: {timezone.localtime().strftime("%d.%m.%Y %H:%M")}'
        meta_width = _text_width(draw, meta_text, meta_font)
        draw.text(
            (PDF_PAGE_WIDTH - PDF_PAGE_MARGIN_X - meta_width, y + 8),
            meta_text,
            font=meta_font,
            fill='#5a6658',
        )
        y += _line_height(draw, title_font) + 18

        if page_number > 1:
            continuation = f'Страница {page_number}'
            draw.text((PDF_PAGE_MARGIN_X, y), continuation, font=meta_font, fill='#5a6658')
            y += _line_height(draw, meta_font) + 12

        y = _draw_pdf_table_header(draw, headers, column_widths, PDF_PAGE_MARGIN_X, y, header_font)
        return image, draw, y

    current_page_number = 1
    image, draw, y = start_page(current_page_number)
    body_line_height = _line_height(draw, body_font)

    if not rows:
        empty_message = 'По выбранным фильтрам записи не найдены.'
        draw.text(
            (PDF_PAGE_MARGIN_X, y + 24),
            empty_message,
            font=body_font,
            fill='#465245',
        )
        pages.append(image)
    else:
        for row_index, row in enumerate(rows):
            wrapped_cells = []
            row_height = 0

            for column_index, cell in enumerate(row):
                max_text_width = column_widths[column_index] - (PDF_CELL_PADDING_X * 2)
                lines = _wrap_pdf_text(draw, cell, body_font, max_text_width)
                wrapped_cells.append(lines)
                row_height = max(
                    row_height,
                    (len(lines) * body_line_height) + (PDF_CELL_PADDING_Y * 2),
                )

            if y + row_height > PDF_PAGE_HEIGHT - PDF_PAGE_MARGIN_Y:
                pages.append(image)
                current_page_number += 1
                image, draw, y = start_page(current_page_number)
                body_line_height = _line_height(draw, body_font)

            x = PDF_PAGE_MARGIN_X
            row_fill = '#ffffff' if row_index % 2 == 0 else '#f7faf6'

            for column_index, lines in enumerate(wrapped_cells):
                width = column_widths[column_index]
                draw.rectangle(
                    [x, y, x + width, y + row_height],
                    fill=row_fill,
                    outline='#bcc7b8',
                    width=1,
                )

                text_y = y + PDF_CELL_PADDING_Y
                for line in lines:
                    draw.text(
                        (x + PDF_CELL_PADDING_X, text_y),
                        line,
                        font=body_font,
                        fill='#1e1e1e',
                    )
                    text_y += body_line_height

                x += width

            y += row_height

        pages.append(image)

    pdf_buffer = io.BytesIO()
    first_page, *other_pages = pages
    first_page.save(
        pdf_buffer,
        format='PDF',
        save_all=True,
        append_images=other_pages,
        resolution=150.0,
    )
    pdf_buffer.seek(0)

    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def get_filtered_users(request):
    users = User.objects.all()

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    role = request.GET.get('role')
    email_verified = request.GET.get('email_verified')
    has_profile = request.GET.get('has_profile')
    gender = request.GET.get('gender')

    if start_date:
        users = users.filter(date_joined__date__gte=parse_date(start_date))
    if end_date:
        users = users.filter(date_joined__date__lte=parse_date(end_date))
    if role:
        users = users.filter(role=role)
    if email_verified == 'yes':
        users = users.filter(email_verified=True)
    elif email_verified == 'no':
        users = users.filter(email_verified=False)
    if has_profile == 'yes':
        from django.db.models import Q
        users = users.filter(Q(first_name__isnull=False, first_name__gt='') |
                             Q(last_name__isnull=False, last_name__gt='') |
                             Q(phone__isnull=False, phone__gt='') |
                             Q(birth_date__isnull=False))
    elif has_profile == 'no':
        from django.db.models import Q
        users = users.filter(
            Q(first_name__isnull=True) | Q(first_name=''),
            Q(last_name__isnull=True) | Q(last_name=''),
            Q(phone__isnull=True) | Q(phone=''),
            birth_date__isnull=True
        )
    if gender == 'M':
        users = users.filter(gender='M')
    elif gender == 'F':
        users = users.filter(gender='F')
    elif gender == 'none':
        from django.db.models import Q
        users = users.filter(Q(gender__isnull=True) | Q(gender=''))

    return users


def apply_users_sorting(users, sort_by):
    if sort_by == 'date_desc':
        return users.order_by('-date_joined')
    elif sort_by == 'date_asc':
        return users.order_by('date_joined')
    elif sort_by == 'username_asc':
        return users.order_by('username')
    elif sort_by == 'username_desc':
        return users.order_by('-username')
    elif sort_by == 'last_login_desc':
        return users.order_by('-last_login')
    elif sort_by == 'last_login_asc':
        return users.order_by('last_login')
    return users.order_by('-date_joined')


@login_required
def users_report(request):
    if not _has_management_access(request.user):
        messages.error(request, 'Доступ запрещен!')
        return redirect('home')

    users = get_filtered_users(request)
    sort_by = request.GET.get('sort_by', 'date_desc')
    users = apply_users_sorting(users, sort_by)

    # Статистика
    all_users = User.objects.all()
    stats = {
        'total': all_users.count(),
        'users': all_users.filter(role='user').count(),
        'owners': all_users.filter(role='owner').count(),
        'admins': all_users.filter(role='admin').count(),
        'managers': all_users.filter(role='manager').count(),
        'with_profile': all_users.exclude(first_name='', last_name='', phone='', birth_date__isnull=True).count(),
    }

    return render(request, 'users_report.html', {
        'users': users,
        'stats': stats,
    })





@login_required
def users_export_pdf(request):
    if not _has_management_access(request.user):
        return HttpResponse('Доступ запрещен', status=403)

    users = get_filtered_users(request)
    sort_by = request.GET.get('sort_by', 'date_desc')
    users = apply_users_sorting(users, sort_by)

    rows = []
    for u in users:
        full_name = ' '.join(filter(None, [u.last_name, u.first_name])) or '—'
        gender_display = 'М' if u.gender == 'M' else ('Ж' if u.gender == 'F' else '—')
        last_login = u.last_login.strftime('%d.%m.%Y %H:%M') if u.last_login else 'Никогда'

        rows.append([
            u.username,
            u.email or '—',
            full_name,
            u.phone or '—',
            gender_display,
            u.get_role_display(),
            u.date_joined.strftime('%d.%m.%Y'),
            last_login,
        ])

    return _build_table_pdf(
        title='Отчёт по пользователям',
        headers=['Логин', 'Email', 'ФИО', 'Телефон', 'Пол', 'Роль', 'Дата регистрации', 'Последний вход'],
        rows=rows,
        filename='users_report.pdf',
        column_fractions=[0.12, 0.19, 0.17, 0.14, 0.06, 0.10, 0.10, 0.12],
    )


# Вынесем фильтрацию в отдельную функцию
def get_filtered_bookings(request):
    bookings = Booking.objects.all()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    room_id = request.GET.get('room')
    status = request.GET.get('status')
    category = request.GET.get('category')

    if start_date:
        bookings = bookings.filter(start_time__date__gte=parse_date(start_date))
    if end_date:
        bookings = bookings.filter(end_time__date__lte=parse_date(end_date))
    if room_id:
        bookings = bookings.filter(room_id=room_id)
    if status:
        bookings = bookings.filter(status=status)
    if category:
        bookings = bookings.filter(room__category=category)
    return bookings


# Страница отчёта
def report_page(request):
    rooms = Room.objects.all()
    # Добавляем строковое представление id, чтобы шаблон не ругался
    for r in rooms:
        r.id_str = str(r.id)

    bookings = get_filtered_bookings(request)

    sort_by = request.GET.get('sort_by', 'date_desc')

    if sort_by == 'date_desc':
        bookings = bookings.order_by('-start_time')
    elif sort_by == 'date_asc':
        bookings = bookings.order_by('start_time')
    elif sort_by == 'time_asc':
        bookings = bookings.order_by('start_time__hour', 'start_time__minute')
    elif sort_by == 'time_desc':
        bookings = bookings.order_by('-start_time__hour', '-start_time__minute')
    elif sort_by == 'room':
        bookings = bookings.order_by('room__name', '-start_time')
    elif sort_by == 'user':
        bookings = bookings.order_by('user__username', '-start_time')

    return render(request, 'report_page.html', {
        'bookings': bookings,
        'rooms': rooms,
        'statuses': STATUS_CHOICES,
        'request': request,
    })





# --- Экспорт в PDF ---
def export_pdf(request):
    bookings = get_filtered_bookings(request)

    sort_by = request.GET.get('sort_by', 'date_desc')

    if sort_by == 'date_desc':
        bookings = bookings.order_by('-start_time')
    elif sort_by == 'date_asc':
        bookings = bookings.order_by('start_time')
    elif sort_by == 'time_asc':
        bookings = bookings.order_by('start_time__hour', 'start_time__minute')
    elif sort_by == 'time_desc':
        bookings = bookings.order_by('-start_time__hour', '-start_time__minute')
    elif sort_by == 'room':
        bookings = bookings.order_by('room__name', '-start_time')
    elif sort_by == 'user':
        bookings = bookings.order_by('user__username', '-start_time')

    category_names = {
        'economy': 'Эконом',
        'standard': 'Стандарт',
        'comfort': 'Комфорт',
        'vip': 'VIP',
        'luxury': 'Люкс'
    }

    rows = []
    for b in bookings:
        start_local = localtime(b.start_time).strftime('%H:%M')
        end_local = localtime(b.end_time).strftime('%H:%M')
        category_display = category_names.get(b.room.category, b.room.category)
        rows.append([
            b.start_time.strftime('%d.%m.%Y'),
            b.room.name,
            category_display,
            b.user.username,
            start_local,
            end_local,
            b.get_status_display(),
        ])

    return _build_table_pdf(
        title='Отчёт по бронированиям',
        headers=['Дата', 'Комната', 'Класс', 'Пользователь', 'Начало', 'Конец', 'Статус'],
        rows=rows,
        filename='bookings.pdf',
        column_fractions=[0.14, 0.24, 0.10, 0.18, 0.10, 0.10, 0.14],
    )


@login_required
def ticket_response_form(request, ticket_id):
    """Возвращает HTML форму для ответа на тикет"""
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
        return render(request, 'ticket_response_form.html', {'ticket': ticket})
    except SupportTicket.DoesNotExist:
        return JsonResponse({'error': 'Тикет не найден'}, status=404)


def _build_faq_sections(include_inactive=False, include_empty=False):
    category_queryset = FAQCategory.objects.all() if include_inactive else FAQCategory.objects.filter(is_active=True)
    categories = list(category_queryset.order_by('order', 'id'))
    faq_queryset = FAQ.objects.all() if include_inactive else FAQ.objects.filter(is_active=True)
    grouped_faqs = {category.slug: [] for category in categories}

    for faq in faq_queryset.order_by('category', 'order', 'id'):
        grouped_faqs.setdefault(faq.category, []).append(faq)

    sections = []
    seen_slugs = set()
    for category in categories:
        items = grouped_faqs.get(category.slug, [])
        if items or include_empty:
            sections.append({
                'code': category.slug,
                'slug': category.slug,
                'label': category.name,
                'items': items,
                'count': len(items),
            })
        seen_slugs.add(category.slug)

    for slug, items in grouped_faqs.items():
        if slug not in seen_slugs and (items or include_empty):
            sections.append({
                'code': slug,
                'slug': slug,
                'label': slug.replace('-', ' ').title(),
                'items': items,
                'count': len(items),
            })

    return sections


def _build_faq_categories():
    categories = []
    for category in FAQCategory.objects.all().order_by('order', 'id'):
        categories.append({
            'id': category.id,
            'name': category.name,
            'slug': category.slug,
            'order': category.order,
            'is_active': category.is_active,
            'count': FAQ.objects.filter(category=category.slug).count(),
        })
    return categories


def _extract_faq_form_data(request):
    question = (request.POST.get('question') or '').strip()
    answer = (request.POST.get('answer') or '').strip()
    category = (request.POST.get('category') or 'general').strip()
    is_active = request.POST.get('is_active') == 'on'

    try:
        order = int(request.POST.get('order') or 0)
    except (TypeError, ValueError):
        return None, 'Порядок должен быть числом.'

    if not question:
        return None, 'Вопрос обязателен.'
    if len(question) < 8:
        return None, 'Вопрос должен содержать минимум 8 символов.'
    if not answer:
        return None, 'Ответ обязателен.'
    if len(answer) < 15:
        return None, 'Ответ должен содержать минимум 15 символов.'
    if not FAQCategory.objects.filter(slug=category).exists():
        return None, 'Выбрана неверная категория FAQ.'

    return {
        'question': question,
        'answer': answer,
        'category': category,
        'order': order,
        'is_active': is_active,
    }, None


def _extract_faq_category_form_data(request, *, existing_category=None):
    name = (request.POST.get('name') or '').strip()
    slug_value = (request.POST.get('slug') or '').strip()
    is_active = request.POST.get('is_active') == 'on'

    try:
        order = int(request.POST.get('order') or 0)
    except (TypeError, ValueError):
        return None, 'Порядок должен быть числом.'

    if not name:
        return None, 'Название категории обязательно.'

    if not slug_value:
        slug_value = slugify(name)

    if not slug_value:
        return None, 'Не удалось сформировать slug категории.'

    existing_query = FAQCategory.objects.filter(slug=slug_value)
    if existing_category is not None:
        existing_query = existing_query.exclude(id=existing_category.id)
    if existing_query.exists():
        return None, 'Категория с таким slug уже существует.'

    return {
        'name': name,
        'slug': slug_value,
        'order': order,
        'is_active': is_active,
    }, None


@login_required
@require_POST
def create_ticket(request):
    """Создание нового тикета"""
    subject = (request.POST.get('subject') or '').strip()
    message = (request.POST.get('message') or '').strip()

    if len(subject) < 5:
        messages.error(request, '❌ Тема обращения должна содержать минимум 5 символов.')
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(reverse('support') + '#new-ticket')

    if len(subject) > 200:
        messages.error(request, '❌ Тема обращения не должна превышать 200 символов.')
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(reverse('support') + '#new-ticket')

    if len(message) < 15:
        messages.error(request, '❌ Опишите проблему подробнее: минимум 15 символов.')
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(reverse('support') + '#new-ticket')

    SupportTicket.objects.create(
        user=request.user,
        subject=subject,
        message=message,
        auto_close_date=None,
    )
    messages.success(request, '✅ Ваш вопрос отправлен в техподдержку!')

    from django.http import HttpResponseRedirect
    from django.urls import reverse
    return HttpResponseRedirect(reverse('support') + '#my-tickets')


def support_view(request):
    """Страница техподдержки с FAQ"""
    faq_sections = _build_faq_sections()
    my_tickets = SupportTicket.objects.none()

    if request.user.is_authenticated:
        my_tickets = SupportTicket.objects.filter(user=request.user).annotate(
            response_count=Count('responses')
        ).order_by('-last_activity', '-created_at')

    can_manage_support = _has_management_access(request.user)
    can_manage_faq = _has_admin_access(request.user)

    context = {
        'my_tickets': my_tickets,
        'faq_sections': faq_sections,
        'faq_total': sum(section['count'] for section in faq_sections),
        'faq_category_total': len(faq_sections),
        'can_manage_support': can_manage_support,
        'can_manage_faq': can_manage_faq,
        'open_my_tickets_count': my_tickets.exclude(status='closed').count() if request.user.is_authenticated else 0,
    }

    if can_manage_support:
        all_tickets = SupportTicket.objects.select_related('user').annotate(
            response_count=Count('responses')
        ).order_by('-last_activity', '-created_at')
        context['all_tickets'] = all_tickets
        context['open_tickets_count'] = all_tickets.exclude(status='closed').count()

    return render(request, 'support_center.html', context)


@login_required
def ticket_detail(request, ticket_id):
    """Детальная страница тикета"""
    try:
        ticket = SupportTicket.objects.select_related('user').prefetch_related('responses__user').get(id=ticket_id)
        can_manage_support = _has_management_access(request.user)

        # Проверяем доступ - разрешаем автору и менеджерам/админам
        if ticket.user != request.user and not can_manage_support:
            if request.method == 'POST':
                return JsonResponse({'success': False, 'error': 'Доступ запрещен.'}, status=403)
            messages.error(request, '❌ Доступ запрещен!')
            return redirect('support')

        if request.method == 'POST':
            response_text = (request.POST.get('response') or '').strip()

            if ticket.status == 'closed':
                return JsonResponse({'success': False, 'error': 'Тикет закрыт. Новые ответы невозможны.'}, status=400)

            if len(response_text) < 3:
                return JsonResponse({'success': False, 'error': 'Ответ должен содержать минимум 3 символа.'}, status=400)

            TicketResponse.objects.create(
                ticket=ticket,
                user=request.user,
                message=response_text
            )

            if can_manage_support:
                ticket.status = 'in_progress'

            ticket.last_activity = timezone.now()
            ticket.auto_close_date = ticket.last_activity + timedelta(days=3) if ticket.status == 'in_progress' else None
            ticket.save()

            return JsonResponse({'success': True, 'message': 'Ответ отправлен!'})

        return render(request, 'ticket_detail_modal.html', {
            'ticket': ticket,
            'can_manage_support': can_manage_support,
            'can_reply': ticket.status != 'closed' and (can_manage_support or ticket.user == request.user),
        })

    except SupportTicket.DoesNotExist:
        if request.method == 'POST':
            return JsonResponse({'success': False, 'error': 'Обращение не найдено.'}, status=404)
        messages.error(request, '❌ Обращение не найдено!')
        return redirect('support')


@login_required
def update_ticket_status(request, ticket_id):
    """Обновление статуса тикета (для менеджеров)"""
    if not _has_management_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен'})

    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
        new_status = request.POST.get('status')
        if new_status in dict(SupportTicket.STATUS_CHOICES):
            ticket.status = new_status
            ticket.save()
            return JsonResponse({'success': True})
    except SupportTicket.DoesNotExist:
        pass

    return JsonResponse({'success': False, 'error': 'Ошибка обновления'})


@login_required
@require_POST
def close_ticket(request, ticket_id):
    """Закрытие тикета пользователем"""
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)

        # Проверяем что пользователь является автором тикета
        if ticket.user != request.user:
            messages.error(request, '❌ Вы можете закрывать только свои обращения!')
            return redirect('support')

        # Меняем статус на закрытый
        ticket.status = 'closed'
        ticket.auto_close_date = None
        ticket.last_activity = timezone.now()
        ticket.save()

        messages.success(request, '✅ Тикет закрыт! Спасибо за обращение.')
        return redirect('support')

    except SupportTicket.DoesNotExist:
        messages.error(request, '❌ Обращение не найдено!')
        return redirect('support')


@login_required
@require_POST
def delete_ticket(request, ticket_id):
    """Удаление тикета менеджером/админом"""
    if not _has_management_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен'})

    try:
        ticket = SupportTicket.objects.get(id=ticket_id)

        # ★★★ ПРОВЕРЯЕМ ЧТО ТИКЕТ НЕ В СТАТУСЕ "ОТКРЫТ" ★★★
        if ticket.status == 'open':
            return JsonResponse({'success': False, 'error': 'Нельзя удалять открытые тикеты'})

        ticket.delete()
        return JsonResponse({'success': True})

    except SupportTicket.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Тикет не найден'})


@login_required
def check_ticket_status(request, ticket_id):
    """Проверка статуса тикета для AJAX"""
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
        if ticket.user != request.user and not _has_management_access(request.user):
            return JsonResponse({'status': 'forbidden'}, status=403)
        return JsonResponse({'status': ticket.status})
    except SupportTicket.DoesNotExist:
        return JsonResponse({'status': 'not_found'})


@login_required
def faq_management(request):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('support')

    faqs = FAQ.objects.all().order_by('category', 'order', 'id')
    categories = FAQCategory.objects.all().order_by('order', 'id')

    return render(request, 'faq_management.html', {
        'faqs': faqs,
        'faq_sections': _build_faq_sections(include_inactive=True, include_empty=True),
        'faq_categories': categories,
        'faq_category_cards': _build_faq_categories(),
        'faq_total': faqs.count(),
        'active_faq_total': faqs.filter(is_active=True).count(),
        'faq_category_total': categories.count(),
        'active_faq_category_total': categories.filter(is_active=True).count(),
    })


@login_required
@require_POST
def create_faq(request):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('support')

    faq_data, error_message = _extract_faq_form_data(request)
    if error_message:
        messages.error(request, f'❌ {error_message}')
        return redirect('faq_management')

    FAQ.objects.create(**faq_data)
    messages.success(request, '✅ FAQ добавлен.')
    return redirect('faq_management')


@login_required
@require_POST
def edit_faq(request, faq_id):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('support')

    try:
        faq = FAQ.objects.get(id=faq_id)
    except FAQ.DoesNotExist:
        messages.error(request, '❌ FAQ не найден.')
        return redirect('faq_management')

    faq_data, error_message = _extract_faq_form_data(request)
    if error_message:
        messages.error(request, f'❌ {error_message}')
        return redirect('faq_management')

    for field, value in faq_data.items():
        setattr(faq, field, value)
    faq.save()

    messages.success(request, '✅ FAQ обновлён.')
    return redirect('faq_management')


@login_required
@require_POST
def delete_faq(request, faq_id):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('support')

    try:
        faq = FAQ.objects.get(id=faq_id)
    except FAQ.DoesNotExist:
        messages.error(request, '❌ FAQ не найден.')
        return redirect('faq_management')

    faq.delete()
    messages.success(request, '✅ FAQ удалён.')
    return redirect('faq_management')


@login_required
@require_POST
def create_faq_category(request):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('support')

    category_data, error_message = _extract_faq_category_form_data(request)
    if error_message:
        messages.error(request, f'❌ {error_message}')
        return redirect('faq_management')

    FAQCategory.objects.create(**category_data)
    messages.success(request, '✅ Категория FAQ добавлена.')
    return redirect('faq_management')


@login_required
@require_POST
def edit_faq_category(request, category_id):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('support')

    try:
        category = FAQCategory.objects.get(id=category_id)
    except FAQCategory.DoesNotExist:
        messages.error(request, '❌ Категория FAQ не найдена.')
        return redirect('faq_management')

    category_data, error_message = _extract_faq_category_form_data(request, existing_category=category)
    if error_message:
        messages.error(request, f'❌ {error_message}')
        return redirect('faq_management')

    old_slug = category.slug
    for field, value in category_data.items():
        setattr(category, field, value)
    category.save()

    if old_slug != category.slug:
        FAQ.objects.filter(category=old_slug).update(category=category.slug)

    messages.success(request, '✅ Категория FAQ обновлена.')
    return redirect('faq_management')


@login_required
@require_POST
def delete_faq_category(request, category_id):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('support')

    try:
        category = FAQCategory.objects.get(id=category_id)
    except FAQCategory.DoesNotExist:
        messages.error(request, '❌ Категория FAQ не найдена.')
        return redirect('faq_management')

    if FAQ.objects.filter(category=category.slug).exists():
        messages.error(request, '❌ Сначала перенесите или удалите FAQ из этой категории.')
        return redirect('faq_management')

    category.delete()
    messages.success(request, '✅ Категория FAQ удалена.')
    return redirect('faq_management')


@login_required
def info_management(request):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('info')

    info_blocks = InfoBlock.objects.all().order_by('section', 'order', 'id')
    sections = InfoSection.objects.all().order_by('order', 'id')

    return render(request, 'info_management.html', {
        'info_blocks': info_blocks,
        'info_sections': _build_info_sections(include_inactive=True, include_empty=True),
        'info_categories': sections,
        'info_section_cards': _build_info_section_cards(),
        'info_total': info_blocks.count(),
        'active_info_total': info_blocks.filter(is_active=True).count(),
        'info_section_total': sections.count(),
        'active_info_section_total': sections.filter(is_active=True).count(),
    })


@login_required
@require_POST
def create_info_block(request):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('info')

    info_data, error_message = _extract_info_block_form_data(request)
    if error_message:
        messages.error(request, f'❌ {error_message}')
        return redirect('info_management')

    InfoBlock.objects.create(**info_data)
    messages.success(request, '✅ Блок информации добавлен.')
    return redirect('info_management')


@login_required
@require_POST
def edit_info_block(request, info_id):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('info')

    try:
        info_block = InfoBlock.objects.get(id=info_id)
    except InfoBlock.DoesNotExist:
        messages.error(request, '❌ Блок информации не найден.')
        return redirect('info_management')

    info_data, error_message = _extract_info_block_form_data(request)
    if error_message:
        messages.error(request, f'❌ {error_message}')
        return redirect('info_management')

    for field, value in info_data.items():
        setattr(info_block, field, value)
    info_block.save()

    messages.success(request, '✅ Блок информации обновлён.')
    return redirect('info_management')


@login_required
@require_POST
def delete_info_block(request, info_id):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('info')

    try:
        info_block = InfoBlock.objects.get(id=info_id)
    except InfoBlock.DoesNotExist:
        messages.error(request, '❌ Блок информации не найден.')
        return redirect('info_management')

    info_block.delete()
    messages.success(request, '✅ Блок информации удалён.')
    return redirect('info_management')


@login_required
@require_POST
def create_info_section(request):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('info')

    section_data, error_message = _extract_info_section_form_data(request)
    if error_message:
        messages.error(request, f'❌ {error_message}')
        return redirect('info_management')

    InfoSection.objects.create(**section_data)
    messages.success(request, '✅ Раздел информации добавлен.')
    return redirect('info_management')


@login_required
@require_POST
def edit_info_section(request, section_id):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('info')

    try:
        section = InfoSection.objects.get(id=section_id)
    except InfoSection.DoesNotExist:
        messages.error(request, '❌ Раздел информации не найден.')
        return redirect('info_management')

    section_data, error_message = _extract_info_section_form_data(request, existing_section=section)
    if error_message:
        messages.error(request, f'❌ {error_message}')
        return redirect('info_management')

    old_slug = section.slug
    for field, value in section_data.items():
        setattr(section, field, value)
    section.save()

    if old_slug != section.slug:
        InfoBlock.objects.filter(section=old_slug).update(section=section.slug)

    messages.success(request, '✅ Раздел информации обновлён.')
    return redirect('info_management')


@login_required
@require_POST
def delete_info_section(request, section_id):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('info')

    try:
        section = InfoSection.objects.get(id=section_id)
    except InfoSection.DoesNotExist:
        messages.error(request, '❌ Раздел информации не найден.')
        return redirect('info_management')

    if InfoBlock.objects.filter(section=section.slug).exists():
        messages.error(request, '❌ Сначала перенесите или удалите блоки из этого раздела.')
        return redirect('info_management')

    section.delete()
    messages.success(request, '✅ Раздел информации удалён.')
    return redirect('info_management')


def login_view(request):
    """Вход в систему (ТОЛЬКО вход)"""
    success_message = request.session.pop('recovery_success_message', None)
    if success_message:
        messages.success(request, success_message)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            # Обычная обработка ошибки
            user_exists = User.objects.filter(username=username).exists()
            if user_exists:
                messages.error(request, 'Неправильный пароль!')
                return render(request, 'login.html', {'username_value': username})
            else:
                messages.error(request, 'Пользователь с таким логином не найден!')
                return render(request, 'login.html', {'username_value': ''})

    return render(request, 'login.html')


def recovery_view(request):
    """Страница восстановления пароля"""
    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'recovery_email')
        print("DEBUG: recovery_view вызван")
        # ★★★ ОБРАБОТКА ВВОДА EMAIL ★★★
        if form_type == 'recovery_email':
            email = request.POST.get('recovery_email')
            print(f"DEBUG: recovery_email = {email}")
            # Ищем пользователя с email
            try:
                user = User.objects.get(email=email)

                # Отправляем код восстановления
                from .email_utils import send_recovery_code
                code = send_recovery_code(user, email)

                # Сохраняем в сессии
                request.session['recovery_user_id'] = user.id
                request.session['recovery_email'] = email

                messages.info(request, f'📧 Код восстановления отправлен на {email}')
                return render(request, 'recovery.html', {
                    'show_recovery_code': True,
                    'recovery_email': email
                })

            except User.DoesNotExist:
                messages.error(request, '❌ Аккаунт с таким email не найден!')
                return render(request, 'recovery.html')

        # ★★★ ОБРАБОТКА КОДА ВОССТАНОВЛЕНИЯ ★★★
        elif form_type == 'recovery_code':
            return handle_password_recovery(request)

    return render(request, 'recovery.html')


def logout_view(request):
    """Выход из системы"""
    # Очищаем все старые сообщения
    storage = messages.get_messages(request)
    for message in storage:
        pass  # Просто очищаем все сообщения

    logout(request)
    messages.success(request, 'Вы успешно вышли из системы!')
    return redirect('home')


def handle_password_recovery(request):
    """Обрабатывает восстановление пароля по коду"""
    recovery_code = request.POST.get('recovery_code')
    new_password = request.POST.get('new_password')
    confirm_password = request.POST.get('confirm_password')

    user_id = request.session.get('recovery_user_id')
    email = request.session.get('recovery_email')

    print(f"DEBUG: recovery_code={recovery_code}, user_id={user_id}, email={email}")

    if not user_id or not email:
        messages.error(request, '❌ Сессия устарела! Начните восстановление заново.')
        return render(request, 'recovery.html')

    try:
        user = User.objects.get(id=user_id)
        confirmation = EmailConfirmation.objects.get(
            user=user,
            email=email,
            code=recovery_code,
            confirmed_at__isnull=True
        )

        if confirmation.is_expired():
            messages.error(request, '❌ Код устарел! Запросите новый.')
            return render(request, 'recovery.html', {
                'show_recovery_code': True,
                'recovery_email': email
            })

        # Проверяем пароли
        if new_password != confirm_password:
            messages.error(request, '❌ Пароли не совпадают!')
            return render(request, 'recovery.html', {
                'show_recovery_code': True,
                'recovery_email': email
            })

        if len(new_password) < 8:
            messages.error(request, '❌ Пароль должен быть не менее 8 символов!')
            return render(request, 'recovery.html', {
                'show_recovery_code': True,
                'recovery_email': email
            })

        # Меняем пароль
        user.set_password(new_password)
        user.save()

        # Подтверждаем код
        confirmation.confirmed_at = timezone.now()
        confirmation.save()

        # Очищаем сессию
        del request.session['recovery_user_id']
        del request.session['recovery_email']
        request.session['failed_attempts'] = 0

        print("DEBUG: Пароль успешно изменен, рендерим login.html с сообщением")
        # ★★★ ПРОСТО РЕНДЕРИМ С СООБЩЕНИЕМ ★★★
        messages.success(request, ' Пароль успешно изменен! Теперь войдите с новым паролем.')
        return render(request, 'login.html')

    except EmailConfirmation.DoesNotExist:
        messages.error(request, '❌ Неверный код восстановления!')
        return render(request, 'recovery.html', {
            'show_recovery_code': True,
            'recovery_email': email
        })


def login_success_view(request):
    """Страница входа с сообщением об успешной смене пароля"""
    messages.success(request, '✅ Пароль успешно изменен! Теперь войдите с новым паролем.')
    # ★★★ НЕ ДЕЛАЕМ РЕДИРЕКТ, А РЕНДЕРИМ СТРАНИЦУ ★★★
    return render(request, 'login.html')


def register(request):
    """Регистрация нового пользователя с двухфакторной аутентификацией"""
    if request.method == 'POST':
        # Проверяем, вводится ли код подтверждения
        confirmation_code = request.POST.get('confirmation_code')
        
        if confirmation_code:
            # Этап 2: Проверка кода подтверждения
            registration_data = request.session.get('registration_data')
            if not registration_data:
                messages.error(request, '❌ Сессия регистрации истекла! Начните заново.')
                return render(request, 'register.html')
            
            username = registration_data.get('username')
            password = registration_data.get('password')
            email = registration_data.get('email')
            
            try:
                # Находим временного пользователя
                user = User.objects.get(username=username, email=email, email_verified=False)
                
                # Проверяем код
                confirmation = EmailConfirmation.objects.get(
                    user=user,
                    email=email,
                    code=confirmation_code,
                    confirmed_at__isnull=True
                )
                
                if confirmation.is_expired():
                    messages.error(request, '❌ Код устарел! Запросите новый.')
                    # Отправляем новый код
                    from .email_utils import send_confirmation_code
                    try:
                        send_confirmation_code(user, email)
                        messages.info(request, f'📧 Новый код отправлен на {email}!')
                    except Exception as e:
                        messages.error(request, f'❌ Ошибка отправки кода: {str(e)}')
                    return render(request, 'register.html', {
                        'show_code_input': True,
                        'registration_email': email
                    })
                
                # Код верный - подтверждаем email
                confirmation.confirmed_at = timezone.now()
                confirmation.save()
                user.email_verified = True
                user.save()
                
                # Очищаем сессию
                del request.session['registration_data']
                
                # Логиним пользователя
                login(request, user)
                messages.success(request, '✅ Регистрация завершена! Email подтвержден.')
                return redirect('home')
                
            except User.DoesNotExist:
                messages.error(request, '❌ Пользователь не найден! Начните регистрацию заново.')
                if 'registration_data' in request.session:
                    del request.session['registration_data']
                return render(request, 'register.html')
            except EmailConfirmation.DoesNotExist:
                messages.error(request, '❌ Неверный код подтверждения!')
                return render(request, 'register.html', {
                    'show_code_input': True,
                    'registration_email': email
                })
        
        else:
            # Этап 1: Создание пользователя и отправка кода
            username = request.POST.get('username')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            email = request.POST.get('email')

            # Валидация
            if not email:
                messages.error(request, '❌ Email обязателен для регистрации!')
                return render(request, 'register.html')
            
            # Проверяем что пароли совпадают
            if password1 != password2:
                messages.error(request, 'Пароли не совпадают!')
                return render(request, 'register.html')

            # Проверяем что пользователь не существует
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Пользователь с таким именем уже существует!')
                return render(request, 'register.html')
            
            # Проверяем что email не занят
            if User.objects.filter(email=email).exists():
                messages.error(request, '❌ Этот email уже используется!')
                return render(request, 'register.html')

            # Создаем пользователя (но не логиним)
            try:
                user = User.objects.create_user(
                    username=username,
                    password=password1,
                    email=email,
                    role='user',
                    email_verified=False,
                )
                
                # Отправляем код подтверждения
                from .email_utils import send_confirmation_code
                try:
                    code = send_confirmation_code(user, email)
                    print(f"КОД ДЛЯ ТЕСТА: {code}")
                    
                    # Сохраняем данные регистрации в сессии
                    request.session['registration_data'] = {
                        'username': username,
                        'password': password1,
                        'email': email
                    }
                    
                    return render(request, 'register.html', {
                        'show_code_input': True,
                        'registration_email': email
                    })
                except Exception as e:
                    # Если не удалось отправить email, удаляем пользователя
                    user.delete()
                    messages.error(request, f'❌ Ошибка отправки кода: {str(e)}')
                    return render(request, 'register.html')
                    
            except Exception as e:
                messages.error(request, f'Ошибка при создании аккаунта: {str(e)}')
                return render(request, 'register.html')

    # GET запрос - показываем форму регистрации
    show_code_input = request.session.get('registration_data') is not None
    registration_email = None
    if show_code_input:
        registration_data = request.session.get('registration_data')
        registration_email = registration_data.get('email') if registration_data else None
    
    return render(request, 'register.html', {
        'show_code_input': show_code_input,
        'registration_email': registration_email
    })


def _build_info_sections(include_inactive=False, include_empty=False):
    section_queryset = InfoSection.objects.all() if include_inactive else InfoSection.objects.filter(is_active=True)
    sections_list = list(section_queryset.order_by('order', 'id'))
    info_queryset = InfoBlock.objects.all() if include_inactive else InfoBlock.objects.filter(is_active=True)
    grouped_blocks = {section.slug: [] for section in sections_list}

    for block in info_queryset.order_by('section', 'order', 'id'):
        grouped_blocks.setdefault(block.section, []).append(block)

    sections = []
    seen_slugs = set()
    for section in sections_list:
        items = grouped_blocks.get(section.slug, [])
        if items or include_empty:
            sections.append({
                'code': section.slug,
                'slug': section.slug,
                'label': section.name,
                'description': section.description,
                'items': items,
                'count': len(items),
            })
        seen_slugs.add(section.slug)

    for slug, items in grouped_blocks.items():
        if slug not in seen_slugs and (items or include_empty):
            sections.append({
                'code': slug,
                'slug': slug,
                'label': slug.replace('-', ' ').title(),
                'description': '',
                'items': items,
                'count': len(items),
            })

    return sections


def _build_info_section_cards():
    cards = []
    for section in InfoSection.objects.all().order_by('order', 'id'):
        cards.append({
            'id': section.id,
            'name': section.name,
            'slug': section.slug,
            'description': section.description,
            'order': section.order,
            'is_active': section.is_active,
            'count': InfoBlock.objects.filter(section=section.slug).count(),
        })
    return cards


def _extract_info_block_form_data(request):
    section = (request.POST.get('section') or 'general').strip()
    title = (request.POST.get('title') or '').strip()
    content = (request.POST.get('content') or '').strip()
    is_active = request.POST.get('is_active') == 'on'

    try:
        order = int(request.POST.get('order') or 0)
    except (TypeError, ValueError):
        return None, 'Порядок должен быть числом.'

    if not InfoSection.objects.filter(slug=section).exists():
        return None, 'Выбран неверный раздел.'
    if not content:
        return None, 'Текст обязателен.'
    if len(content) < 5:
        return None, 'Текст должен содержать минимум 5 символов.'
    if section in {'rules', 'contacts'} and not title:
        return None, 'Для этого раздела нужен заголовок.'

    return {
        'section': section,
        'title': title,
        'content': content,
        'order': order,
        'is_active': is_active,
    }, None


def _extract_info_section_form_data(request, *, existing_section=None):
    name = (request.POST.get('name') or '').strip()
    slug_value = (request.POST.get('slug') or '').strip()
    description = (request.POST.get('description') or '').strip()
    is_active = request.POST.get('is_active') == 'on'

    try:
        order = int(request.POST.get('order') or 0)
    except (TypeError, ValueError):
        return None, 'Порядок должен быть числом.'

    if not name:
        return None, 'Название раздела обязательно.'

    if not slug_value:
        slug_value = slugify(name)

    if not slug_value:
        return None, 'Не удалось сформировать slug раздела.'

    existing_query = InfoSection.objects.filter(slug=slug_value)
    if existing_section is not None:
        existing_query = existing_query.exclude(id=existing_section.id)
    if existing_query.exists():
        return None, 'Раздел с таким slug уже существует.'

    return {
        'name': name,
        'slug': slug_value,
        'description': description,
        'order': order,
        'is_active': is_active,
    }, None


def info_page(request):
    """Страница с информацией, правилами и инструкциями"""
    info_sections = _build_info_sections(include_empty=True)
    can_manage_info = _has_admin_access(request.user)
    active_info_blocks = sum(section['count'] for section in info_sections)

    return render(request, 'info.html', {
        'info_sections': info_sections,
        'info_total': active_info_blocks,
        'info_section_total': len(info_sections),
        'can_manage_info': can_manage_info,
    })


def home(request):
    """Главная страница"""

    category = request.GET.get('category')
    office_id = request.GET.get('office')

    # Подгружаем office заранее
    if _has_management_access(request.user):
        rooms = Room.objects.select_related("office").all()
    else:
        rooms = Room.objects.select_related("office").filter(status='active')

    # Фильтр по категории
    if category:
        rooms = rooms.filter(category=category)

    # Фильтр по офису
    if office_id:
        rooms = rooms.filter(office_id=office_id)

    # Список офисов для фильтра
    offices = Office.objects.filter(is_active=True)
    categories = Room.CATEGORY_CHOICES

    # Получаем последние бронирования пользователя (если авторизован)
    recent_bookings = []
    if request.user.is_authenticated:
        recent_bookings = Booking.objects.filter(user=request.user).select_related('room').order_by('-created_at')[:5]

    main_page_messages = [
        message
        for message in messages.get_messages(request)
        if message.level >= messages.WARNING
    ]

    return render(request, 'home.html', {
        'rooms': rooms,
        'offices': offices,
        'categories': categories,
        'selected_category': category,
        'selected_office': office_id,
        'recent_bookings': recent_bookings,
        'page_messages': main_page_messages,
    })


def _save_room_image_file(uploaded_file):
    fs = FileSystemStorage(location=settings.MEDIA_ROOT / 'rooms')
    filename = fs.save(uploaded_file.name, uploaded_file)
    return f'rooms/{filename}'


def _parse_optional_int(raw_value):
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _extract_room_image_uploads(request, allow_gallery_fallback=True):
    primary_image = request.FILES.get('image')
    extra_images = [image for image in request.FILES.getlist('gallery_images') if image]
    selected_pending_cover_index = _parse_optional_int(request.POST.get('selected_pending_cover_index'))

    if (
        not primary_image
        and extra_images
        and selected_pending_cover_index is not None
        and 0 <= selected_pending_cover_index < len(extra_images)
    ):
        primary_image = extra_images.pop(selected_pending_cover_index)
    elif not primary_image and allow_gallery_fallback and extra_images:
        primary_image = extra_images.pop(0)

    return primary_image, extra_images


def _parse_gallery_image_ids(raw_ids):
    parsed_ids = []

    for raw_id in raw_ids:
        try:
            parsed_ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue

    return parsed_ids


def _parse_gallery_order(raw_value):
    if not raw_value:
        return []

    return _parse_gallery_image_ids([chunk.strip() for chunk in str(raw_value).split(',') if chunk.strip()])


def _parse_equipment_ids(raw_value):
    if not raw_value:
        return []

    if isinstance(raw_value, (list, tuple)):
        raw_chunks = raw_value
    else:
        raw_chunks = [chunk.strip() for chunk in str(raw_value).split(',') if chunk.strip()]

    parsed_ids = []
    seen_ids = set()

    for raw_chunk in raw_chunks:
        equipment_id = _parse_optional_int(raw_chunk)
        if equipment_id is None or equipment_id in seen_ids:
            continue
        parsed_ids.append(equipment_id)
        seen_ids.add(equipment_id)

    return parsed_ids


def _serialize_equipment_catalog(equipment_queryset=None):
    if equipment_queryset is None:
        equipment_queryset = Equipment.objects.filter(is_active=True).order_by('name')
    room_categories = dict(Room.CATEGORY_CHOICES)

    return [
        {
            'id': equipment.id,
            'name': equipment.name,
            'categories': equipment.categories or [],
            'category_labels': [room_categories.get(category, category) for category in (equipment.categories or [])],
            'is_active': equipment.is_active,
            'rooms_count': getattr(equipment, 'rooms_count', None),
        }
        for equipment in equipment_queryset
    ]


def _resolve_selected_equipment(raw_value, category):
    selected_equipment_ids = _parse_equipment_ids(raw_value)
    if not selected_equipment_ids:
        return []

    equipment_by_id = {
        equipment.id: equipment
        for equipment in Equipment.objects.filter(id__in=selected_equipment_ids, is_active=True)
    }

    missing_ids = [equipment_id for equipment_id in selected_equipment_ids if equipment_id not in equipment_by_id]
    if missing_ids:
        raise ValueError('Часть выбранного оборудования не найдена или уже отключена.')

    selected_equipment = [equipment_by_id[equipment_id] for equipment_id in selected_equipment_ids]
    unavailable_equipment = [equipment.name for equipment in selected_equipment if not equipment.is_available_for_category(category)]

    if unavailable_equipment:
        raise ValueError(
            'Для этой категории комнаты недоступно оборудование: ' + ', '.join(unavailable_equipment)
        )

    return selected_equipment


def _sync_room_equipment(room, selected_equipment):
    selected_equipment = selected_equipment or []
    room.equipment = '\n'.join(equipment.name for equipment in selected_equipment)
    room.save(update_fields=['equipment'])
    room.equipment_items.set(selected_equipment)


def _sync_rooms_equipment(room_ids):
    if not room_ids:
        return

    for room in Room.objects.filter(id__in=room_ids).prefetch_related('equipment_items'):
        room.equipment = '\n'.join(room.equipment_items.order_by('name').values_list('name', flat=True))
        room.save(update_fields=['equipment'])


def _validate_room_image_limit(room, primary_image=None, extra_images=None, removed_gallery_ids=None):
    extra_images = extra_images or []
    removed_gallery_ids = removed_gallery_ids or []

    if room.pk:
        remaining_extra_count = room.gallery_images.exclude(id__in=removed_gallery_ids).count()
    else:
        remaining_extra_count = 0

    has_primary_after = bool(primary_image or room.image)
    total_images_after = (1 if has_primary_after else 0) + remaining_extra_count + len(extra_images)

    if total_images_after > Room.MAX_TOTAL_IMAGES:
        raise ValueError(f'Можно сохранить не более {Room.MAX_TOTAL_IMAGES} фото для одной комнаты.')


def _append_room_gallery_images(room, uploaded_images):
    if not uploaded_images:
        return

    current_max_order = room.gallery_images.aggregate(max_order=Max('sort_order'))['max_order'] or 0

    for offset, uploaded_image in enumerate(uploaded_images, start=1):
        RoomImage.objects.create(
            room=room,
            image=_save_room_image_file(uploaded_image),
            sort_order=current_max_order + offset,
        )


def _apply_room_gallery_order(room, ordered_gallery_ids):
    if not ordered_gallery_ids:
        return

    gallery_images = list(room.gallery_images.all())
    if not gallery_images:
        return

    images_by_id = {image.id: image for image in gallery_images}
    ordered_images = []
    seen_ids = set()

    for image_id in ordered_gallery_ids:
        if image_id in images_by_id and image_id not in seen_ids:
            ordered_images.append(images_by_id[image_id])
            seen_ids.add(image_id)

    ordered_images.extend(image for image in gallery_images if image.id not in seen_ids)

    images_to_update = []
    for position, image in enumerate(ordered_images, start=1):
        if image.sort_order != position:
            image.sort_order = position
            images_to_update.append(image)

    if images_to_update:
        RoomImage.objects.bulk_update(images_to_update, ['sort_order'])


def _promote_gallery_image_to_cover(room, gallery_image_id):
    if gallery_image_id is None:
        return

    gallery_image = room.gallery_images.filter(id=gallery_image_id).first()
    if not gallery_image or not gallery_image.image:
        raise ValueError('Выбранное фото для обложки не найдено.')

    previous_cover_name = room.image.name if room.image else None
    promoted_image_name = gallery_image.image.name
    promoted_sort_order = gallery_image.sort_order

    room.image = promoted_image_name
    room.save(update_fields=['image'])
    gallery_image.delete()

    if previous_cover_name and previous_cover_name != promoted_image_name:
        RoomImage.objects.create(
            room=room,
            image=previous_cover_name,
            sort_order=promoted_sort_order,
        )


def _build_room_gallery(room):
    gallery = []
    photo_index = 1

    if room.image:
        gallery.append({
            'id': 'primary',
            'url': room.image.url,
            'alt': f'{room.name} — фото {photo_index}',
            'is_primary': True,
        })
        photo_index += 1

    for gallery_image in room.gallery_images.all():
        if not gallery_image.image:
            continue

        gallery.append({
            'id': gallery_image.id,
            'url': gallery_image.image.url,
            'alt': f'{room.name} — фото {photo_index}',
            'is_primary': False,
        })
        photo_index += 1

    return gallery


def _build_room_gallery_payload(room):
    return [
        {
            'id': gallery_image.id,
            'url': gallery_image.image.url,
        }
        for gallery_image in room.gallery_images.all()
        if gallery_image.image
    ]


def _get_visible_room(request, room_id):
    try:
        room = Room.objects.select_related('office').prefetch_related('gallery_images').get(id=room_id)
    except Room.DoesNotExist:
        messages.error(request, '❌ Комната не найдена!')
        return None

    if not _has_management_access(request.user):
        if room.status != 'active':
            messages.error(request, '❌ Эта комната временно недоступна!')
            return None

    return room


def room_detail(request, room_id):
    """Страница комнаты"""
    room = _get_visible_room(request, room_id)
    if room is None:
        return redirect('home')

    reviews = Review.objects.filter(room=room, status='approved').order_by('-created_at')
    room_gallery = _build_room_gallery(room)

    return render(request, 'room_detail.html', {
        'room': room,
        'reviews': reviews,
        'room_gallery': room_gallery,
        'booking_page': False,
    })


def room_booking_page(request, room_id):
    """Отдельная страница бронирования комнаты"""
    room = _get_visible_room(request, room_id)
    if room is None:
        return redirect('home')

    return render(request, 'room_detail.html', {
        'room': room,
        'room_gallery': _build_room_gallery(room),
        'booking_page': True,
    })


@login_required
def profile_view(request):
    """Страница профиля со статистикой активности"""
    user = request.user

    # Получаем все бронирования пользователя
    user_bookings = Booking.objects.filter(user=user)

    # Статистика бронирований
    total_bookings = user_bookings.count()
    completed_bookings = user_bookings.filter(status='completed').count()

    # ★★★ ПРОСТОЙ РАСЧЕТ: успешные от всех бронирований ★★★
    if total_bookings > 0:
        activity_percentage = (completed_bookings / total_bookings) * 100
    else:
        activity_percentage = 0

    return render(request, 'profile.html', {
        'user': user,
        'bookings_count': total_bookings,
        'activity_percentage': round(activity_percentage),
    })


def _build_user_activity_maps(user_ids):
    user_ids = list(user_ids)
    if not user_ids:
        return {}

    bookings_map = {
        row['user_id']: row['total']
        for row in Booking.objects.filter(user_id__in=user_ids).values('user_id').annotate(total=Count('id'))
    }
    tickets_map = {
        row['user_id']: row['total']
        for row in SupportTicket.objects.filter(user_id__in=user_ids).values('user_id').annotate(total=Count('id'))
    }
    ticket_responses_map = {
        row['user_id']: row['total']
        for row in TicketResponse.objects.filter(user_id__in=user_ids).values('user_id').annotate(total=Count('id'))
    }
    reviews_map = {
        row['user_id']: row['total']
        for row in Review.objects.filter(user_id__in=user_ids).values('user_id').annotate(total=Count('id'))
    }
    review_replies_map = {
        row['user_id']: row['total']
        for row in ReviewReply.objects.filter(user_id__in=user_ids).values('user_id').annotate(total=Count('id'))
    }

    activity_maps = {}
    for user_id in user_ids:
        activity_snapshot = {
            'bookings': bookings_map.get(user_id, 0),
            'tickets': tickets_map.get(user_id, 0),
            'ticket_responses': ticket_responses_map.get(user_id, 0),
            'reviews': reviews_map.get(user_id, 0),
            'review_replies': review_replies_map.get(user_id, 0),
        }
        activity_snapshot['has_activity'] = any(activity_snapshot.values())
        activity_maps[user_id] = activity_snapshot

    return activity_maps


def _format_user_activity_summary(activity_snapshot):
    activity_snapshot = activity_snapshot or {}
    summary_parts = []

    if activity_snapshot.get('bookings'):
        summary_parts.append(f"броней: {activity_snapshot['bookings']}")
    if activity_snapshot.get('tickets'):
        summary_parts.append(f"тикетов: {activity_snapshot['tickets']}")
    if activity_snapshot.get('ticket_responses'):
        summary_parts.append(f"ответов ТП: {activity_snapshot['ticket_responses']}")
    if activity_snapshot.get('reviews'):
        summary_parts.append(f"отзывов: {activity_snapshot['reviews']}")
    if activity_snapshot.get('review_replies'):
        summary_parts.append(f"ответов на отзывы: {activity_snapshot['review_replies']}")

    if not summary_parts:
        return 'Связанных данных нет'

    return ', '.join(summary_parts)


def _has_admin_access(user):
    return bool(getattr(user, 'is_authenticated', False)) and (
        getattr(user, 'is_superuser', False) or getattr(user, 'role', None) in ['owner', 'admin']
    )


def _has_management_access(user):
    return bool(getattr(user, 'is_authenticated', False)) and (
        getattr(user, 'is_superuser', False) or getattr(user, 'role', None) in ['owner', 'admin', 'manager']
    )


def _build_admin_user_policy(actor, target_user, activity_snapshot=None, admin_count=None):
    activity_snapshot = activity_snapshot or {}
    owner_count = User.objects.filter(role='owner').count()
    admin_count = admin_count if admin_count is not None else User.objects.filter(role='admin').count()

    policy = {
        'can_view': _has_admin_access(actor),
        'can_change_role': False,
        'can_delete': False,
        'allowed_roles': [],
        'role_change_reason': '',
        'delete_reason': '',
        'activity_summary': _format_user_activity_summary(activity_snapshot),
        'has_activity': bool(activity_snapshot.get('has_activity')),
    }

    if not _has_admin_access(actor):
        policy['role_change_reason'] = 'Только администратор может менять роли.'
        policy['delete_reason'] = 'Только администратор может удалять пользователей.'
        return policy

    if target_user.is_superuser:
        policy['role_change_reason'] = 'Суперпользователь управляется отдельно.'
        policy['delete_reason'] = 'Суперпользователь через панель не удаляется.'
        return policy

    if target_user.id == actor.id:
        if getattr(actor, 'role', None) == 'admin' and owner_count == 0:
            policy['can_change_role'] = True
            policy['allowed_roles'] = ['owner']
            policy['role_change_reason'] = 'Owner ещё не создан. Можно назначить owner самому себе.'
        else:
            policy['role_change_reason'] = 'Нельзя менять роль самому себе.'
        policy['delete_reason'] = 'Нельзя удалить свой аккаунт.'
        return policy

    if target_user.role == 'owner':
        if getattr(actor, 'role', None) == 'owner':
            policy['can_change_role'] = True
            policy['allowed_roles'] = ['admin', 'manager', 'user']
            policy['role_change_reason'] = 'Владельца можно понизить, но нельзя назначать еще одного владельца.'
            policy['delete_reason'] = 'Владельца можно понизить, но нельзя удалить через панель.'
            return policy

        policy['role_change_reason'] = 'Владелец управляется отдельно.'
        policy['delete_reason'] = 'Владелец через панель не удаляется.'
        return policy

    if getattr(actor, 'role', None) == 'owner':
        policy['can_change_role'] = True
        policy['allowed_roles'] = ['admin', 'manager', 'user']
        policy['role_change_reason'] = 'Владелец может менять роли администраторов, менеджеров и пользователей, но не создавать второго владельца.'

        if activity_snapshot.get('has_activity'):
            policy['delete_reason'] = f"Нельзя удалить пользователя с историей: {policy['activity_summary']}."
        else:
            policy['can_delete'] = True
            policy['delete_reason'] = 'Пользователь может быть удалён, связанных данных нет.'
        return policy

    if target_user.role == 'admin':
        if admin_count > 1:
            policy['role_change_reason'] = 'Обычный админ не управляет другими администраторами.'
        else:
            policy['role_change_reason'] = 'Последнего администратора нельзя понизить.'

        policy['delete_reason'] = 'Администраторы через панель не удаляются.'
        return policy

    policy['can_change_role'] = True
    policy['allowed_roles'] = ['manager', 'user']
    policy['role_change_reason'] = 'Администратор может менять роли менеджеров и пользователей.'

    if activity_snapshot.get('has_activity'):
        policy['delete_reason'] = f"Нельзя удалить пользователя с историей: {policy['activity_summary']}."
    else:
        policy['can_delete'] = True
        policy['delete_reason'] = 'Пользователь может быть удалён, связанных данных нет.'

    return policy


@login_required
def admin_panel(request):
    """Админ-панель управления системой"""
    # Проверяем что пользователь админ
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('home')

    role_order = {'owner': 0, 'admin': 1, 'manager': 2, 'user': 3}
    users = list(User.objects.all())
    users.sort(key=lambda user: (role_order.get(user.role, 99), user.username.lower()))
    admin_count = sum(1 for user in users if user.role == 'admin')
    activity_maps = _build_user_activity_maps([user.id for user in users])

    for user in users:
        admin_policy = _build_admin_user_policy(
            actor=request.user,
            target_user=user,
            activity_snapshot=activity_maps.get(user.id, {}),
            admin_count=admin_count,
        )
        user.admin_policy = admin_policy
        user.admin_activity_summary = admin_policy['activity_summary']

    return render(request, 'admin_panel.html', {'users': users})


@login_required
def manager_panel(request):
    """Менеджерская панель для подтверждения бронирований"""
    if not _has_management_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('home')

    bookings = Booking.objects.all().order_by('-created_at')
    rooms = Room.objects.all()

    from django.utils.timezone import get_current_timezone

    for booking in bookings:
        tz = get_current_timezone()
        local_start = booking.start_time.astimezone(tz)
        local_end = booking.end_time.astimezone(tz)

        # Сохраняем как строки чтобы избежать конвертации в шаблоне
        booking.date_display = local_start.strftime("%d.%m.%Y")
        booking.time_display = f"{local_start.strftime('%H:%M')} - {local_end.strftime('%H:%M')}"

        # ★★★ НЕ присваиваем duration_hours и total_price - они теперь свойства ★★★

    return render(request, 'manager_panel.html', {
        'bookings': bookings,
        'rooms': rooms
    })


@login_required
def delete_booking(request, booking_id):
    """Удаление бронирования (для менеджеров)"""
    if not _has_management_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен'})

    try:
        booking = Booking.objects.get(id=booking_id)
        booking.delete()

        messages.success(request, '✅ Бронирование успешно удалено!')
        return JsonResponse({'success': True})

    except Booking.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Бронирование не найдено'})


@login_required
def update_booking_status(request, booking_id):
    if not _has_management_access(request.user):
        return JsonResponse({'success': False, 'error': 'Нет доступа'})

    try:
        booking = Booking.objects.get(id=booking_id)
        data = json.loads(request.body)

        new_status = data.get('status')
        new_price = data.get('total_price')
        manager_comment = data.get('manager_comment')

        # ★★★ СОХРАНЯЕМ ИЗМЕНЕННУЮ ЦЕНУ ★★★
        if new_price:
            booking.custom_price = Decimal(new_price)

        # Менеджер оставил комментарий
        if manager_comment is not None:
            booking.manager_comment = manager_comment

        # Меняем статус
        if new_status in dict(Booking.STATUS_CHOICES):
            booking.status = new_status

        booking.save()

        # Если подтверждено — отправляем письмо с ПРАВИЛЬНОЙ ценой
        if new_status == "confirmed":
            from .email_booking import send_booking_confirmation
            send_booking_confirmation(booking)

        return JsonResponse({'success': True})

    except Booking.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Бронь не найдена'})


@login_required
def admin_user_profile(request, user_id):
    """Просмотр профиля пользователя для админа"""
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('home')

    try:
        user = User.objects.get(id=user_id)
        admin_policy = _build_admin_user_policy(
            actor=request.user,
            target_user=user,
            activity_snapshot=_build_user_activity_maps([user.id]).get(user.id, {}),
            admin_count=User.objects.filter(role='admin').count(),
        )

        # Получаем бронирования пользователя
        user_bookings = Booking.objects.filter(user=user).order_by('-created_at')
        bookings_count = user_bookings.count()
        active_bookings_count = user_bookings.filter(status__in=['pending', 'confirmed']).count()
        completed_bookings_count = user_bookings.filter(status='completed').count()
        cancelled_bookings_count = user_bookings.filter(status='cancelled').count()

        return render(request, 'admin_user_profile.html', {
            'target_user': user,
            'admin_policy': admin_policy,
            'user_bookings': user_bookings,
            'bookings_count': bookings_count,
            'active_bookings_count': active_bookings_count,
            'completed_bookings_count': completed_bookings_count,
            'cancelled_bookings_count': cancelled_bookings_count
        })
    except User.DoesNotExist:
        messages.error(request, '❌ Пользователь не найден!')
        return redirect('admin_panel')


@login_required
def update_profile(request):
    """Обновление данных профиля"""
    if request.method == 'POST':
        user = request.user
        username = request.POST.get('username')
        phone = request.POST.get('phone')
        avatar = request.FILES.get('avatar')

        # ★★★ НОВЫЕ ПОЛЯ ★★★
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        patronymic = request.POST.get('patronymic')
        birth_date = request.POST.get('birth_date')
        gender = request.POST.get('gender')

        # Проверяем username
        if username and username != user.username:
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                messages.error(request, '❌ Это имя пользователя уже занято!')
                return redirect('profile')
            user.username = username

        if phone is not None:
            # Remove all non-digits
            phone_digits = re.sub(r'\D', '', phone)

            # Empty phone is allowed
            if phone_digits == '' or phone_digits == '7':
                user.phone = ''
            elif len(phone_digits) == 11 and phone_digits.startswith('7'):
                # Format: +7 (XXX) XXX-XX-XX
                formatted_phone = f"+7 ({phone_digits[1:4]}) {phone_digits[4:7]}-{phone_digits[7:9]}-{phone_digits[9:11]}"
                user.phone = formatted_phone
            else:
                messages.error(request, '❌ Некорректный формат телефона! Используйте формат: +7 (XXX) XXX-XX-XX')
                return redirect('profile')

        # ★★★ СОХРАНЯЕМ НОВЫЕ ПОЛЯ ★★★
        user.first_name = first_name
        user.last_name = last_name
        user.patronymic = patronymic
        user.gender = gender

        if birth_date:
            user.birth_date = birth_date

        # Сохраняем аватар
        if avatar:
            fs = FileSystemStorage(location=settings.MEDIA_ROOT / 'avatars')
            filename = fs.save(avatar.name, avatar)
            user.avatar = f'avatars/{filename}'

        # Сохраняем пользователя
        try:
            user.save()
            messages.success(request, '✅ Профиль успешно обновлён!')
        except Exception as e:
            messages.error(request, f'❌ Ошибка при обновлении профиля: {str(e)}')

        return redirect('profile')
    return redirect('profile')


@login_required
def verify_email(request):
    """Подтверждение email"""
    if request.method == 'POST':
        user = request.user
        email = request.POST.get('email')
        confirmation_code = request.POST.get('confirmation_code')

        # Если отправляем код
        if email and not confirmation_code:
            # Проверяем не занят ли email другим пользователем
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                messages.error(request, '❌ Этот email уже используется!')
                return redirect('profile')

            # Отправляем код подтверждения
            from .email_utils import send_confirmation_code
            try:
                code = send_confirmation_code(user, email)
                messages.info(request, f'📧 Код подтверждения отправлен на {email}!')
                print(f"КОД ДЛЯ ТЕСТА: {code}")
                # Сохраняем email во временную переменную сессии
                request.session['pending_email'] = email
            except Exception as e:
                messages.error(request, f'❌ Ошибка отправки кода: {str(e)}')

        # Если вводим код
        elif confirmation_code:
            pending_email = request.session.get('pending_email')
            if not pending_email:
                messages.error(request, '❌ Сначала укажите email и отправьте код!')
                return redirect('profile')

            try:
                confirmation = EmailConfirmation.objects.get(
                    user=user,
                    code=confirmation_code,
                    confirmed_at__isnull=True
                )

                if confirmation.is_expired():
                    messages.error(request, '❌ Код устарел! Запросите новый.')
                else:
                    # Подтверждаем email и сохраняем
                    confirmation.confirmed_at = timezone.now()
                    confirmation.save()
                    user.email = pending_email
                    user.save()
                    # Очищаем временные данные
                    del request.session['pending_email']
                    messages.success(request, '✅ Email успешно подтвержден и сохранен!')

            except EmailConfirmation.DoesNotExist:
                messages.error(request, '❌ Неверный код подтверждения!')

        return redirect('profile')
    return redirect('profile')


@login_required
def get_available_rooms(request):
    """AJAX: Получить доступные комнаты"""
    date = request.GET.get('date')
    start_time = request.GET.get('start_time')
    duration = request.GET.get('duration')
    participants = request.GET.get('participants')

    # Здесь логика проверки доступности комнат
    rooms = Room.objects.filter(is_active=True)

    # Фильтрация по вместимости
    if participants and int(participants) > 0:
        rooms = rooms.filter(capacity__gte=int(participants))

    # TODO: Проверка занятости по времени
    available_rooms = []
    for room in rooms:
        available_rooms.append({
            'id': room.id,
            'name': room.name,
            'capacity': room.capacity,
            'location': room.location,
            'price_per_hour': room.price_per_hour,
            'amenities': room.amenities
        })

    return JsonResponse({'rooms': available_rooms})


@login_required
def create_booking(request):
    """Создать бронирование со страницы комнаты"""
    if request.method == 'POST':
        try:
            room_id = request.POST.get('room_id')
            booking_origin = request.POST.get('booking_origin')
            date_str = request.POST.get('selected_date')
            time_str = request.POST.get('start_time')
            duration = request.POST.get('duration')

            # ★★★ ПОЛУЧАЕМ ДАННЫЕ ИЗ ФОРМЫ ★★★
            booking_full_name = request.POST.get('booking_full_name')
            booking_email = request.POST.get('booking_email')
            booking_phone = request.POST.get('booking_phone')
            comment = request.POST.get('comment')

            print(f"🔍 ДЕБАГ: Получены данные:")
            print(f"  - ФИО: {booking_full_name}")
            print(f"  - Email: {booking_email}")
            print(f"  - Телефон: {booking_phone}")

            # Получаем комнату
            room = Room.objects.get(id=room_id)

            # Создаем datetime
            from django.utils.timezone import make_aware
            from zoneinfo import ZoneInfo

            naive_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            start_datetime = make_aware(naive_datetime, timezone=ZoneInfo("Asia/Irkutsk"))
            end_datetime = start_datetime + timedelta(hours=int(duration))

            # Проверяем что бронирование в будущем
            if start_datetime < timezone.now():
                messages.error(request, '❌ Нельзя бронировать в прошлом!')
                if booking_origin == 'room_booking':
                    return redirect('room_booking', room_id=room_id)
                return redirect('room_detail', room_id=room_id)

            # Проверяем доступность комнаты
            overlapping = Booking.objects.filter(
                room=room,
                start_time__lt=end_datetime,
                end_time__gt=start_datetime,
                status__in=['pending', 'confirmed']
            ).exists()

            if overlapping:
                messages.error(request, '❌ Комната уже занята в это время!')
                if booking_origin == 'room_booking':
                    return redirect('room_booking', room_id=room_id)
                return redirect('room_detail', room_id=room_id)

            # ★★★ СОХРАНЯЕМ ДАННЫЕ В ПРОФИЛЬ ЕСЛИ ИЗМЕНИЛИСЬ ★★★
            if booking_email and booking_email != request.user.email:
                request.user.email = booking_email

                # ★★★ ПРОВЕРЯЕМ, НЕ ПОДТВЕРЖДЕН ЛИ УЖЕ ЭТОТ EMAIL В ДРУГОМ ПОЛЬЗОВАТЕЛЕ? ★★★
                from .models import EmailConfirmation
                try:
                    # Проверяем, есть ли подтверждение для этого email у текущего пользователя
                    confirmation = EmailConfirmation.objects.filter(
                        user=request.user,
                        email=booking_email,
                        confirmed_at__isnull=False
                    ).first()

                    if confirmation and not confirmation.is_expired():
                        # Если email уже был подтвержден этим пользователем ранее
                        request.user.email_verified = True
                        messages.info(request, f'📧 Email {booking_email} уже подтвержден ранее!')
                    else:
                        # Если email новый или не подтвержден
                        request.user.email_verified = False
                        messages.info(request, '📧 Email обновлен! Подтвердите его в профиле.')
                except Exception as e:
                    # В случае ошибки просто сбрасываем подтверждение
                    request.user.email_verified = False
                    print(f"⚠️ Ошибка при проверке подтверждения email: {e}")

                request.user.save()

            if booking_phone and booking_phone != request.user.phone:
                request.user.phone = booking_phone
                request.user.save()

            # ★★★ СОЗДАЕМ БРОНИРОВАНИЕ С КОНТАКТНЫМИ ДАННЫМИ ★★★
            booking = Booking.objects.create(
                user=request.user,
                room=room,
                start_time=start_datetime,
                end_time=end_datetime,
                status='pending',
                booking_full_name=booking_full_name,
                booking_email=booking_email,
                booking_phone=booking_phone,
                manager_comment=comment if comment else ''  # Сохраняем комментарий клиента в manager_comment
            )

            print(f"✅ БРОНИРОВАНИЕ СОЗДАНО!")
            print(f"   Контактное лицо: {booking_full_name}")
            print(f"   Email для уведомлений: {booking_email}")

            messages.success(request, '✅ Запрос на бронирование отправлен! Ожидайте подтверждения.')
            return redirect('home')

        except Exception as e:
            print(f"❌ ОШИБКА ПРИ БРОНИРОВАНИИ: {str(e)}")
            messages.error(request, f'❌ Ошибка при бронировании: {str(e)}')
            if booking_origin == 'room_booking':
                return redirect('room_booking', room_id=room_id)
            return redirect('room_detail', room_id=room_id)

    return redirect('home')


@login_required
def get_available_times(request, room_id):
    """AJAX: Получить доступное время для комнаты на дату"""
    date_str = request.GET.get('date')

    try:
        room = Room.objects.get(id=room_id)
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Все возможные слоты времени
        time_slots = []
        for hour in range(9, 20):
            time_slots.append(f"{hour:02d}:00")

        # Получаем бронирования
        bookings = Booking.objects.filter(
            room=room,
            start_time__date=selected_date,
            status__in=['pending', 'confirmed']
        )

        # Конвертируем в локальное время
        from django.utils.timezone import localtime

        # Создаем список занятого времени
        booked_slots = []
        for booking in bookings:
            local_start = localtime(booking.start_time)
            local_end = localtime(booking.end_time)

            current_time = local_start
            while current_time < local_end:
                time_str = current_time.strftime("%H:%M")
                booked_slots.append(time_str)
                current_time += timedelta(hours=1)

        available_slots = [slot for slot in time_slots if slot not in booked_slots]

        return JsonResponse({
            'available_times': available_slots,
            'booked_times': booked_slots
        })

    except Exception as e:
        print(f"❌ Ошибка в get_available_times: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

    except Exception as e:
        print(f"❌ ОШИБКА в get_available_times: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def update_avatar(request):
    """Обновление только аватарки"""
    if request.method == 'POST':
        user = request.user
        avatar = request.FILES.get('avatar')

        if avatar:
            fs = FileSystemStorage(location=settings.MEDIA_ROOT / 'avatars')
            filename = fs.save(avatar.name, avatar)
            user.avatar = f'avatars/{filename}'
            user.save()
            messages.success(request, '✅ Аватарка успешно обновлена!')
        else:
            messages.error(request, '❌ Выберите файл для аватарки!')

        return redirect('profile')
    return redirect('profile')


@login_required
def add_room(request):
    """Добавление новой комнаты - только админ"""
    if not _has_admin_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен!'})

    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            location = request.POST.get('location')
            capacity = request.POST.get('capacity')
            price_per_hour = request.POST.get('price_per_hour')
            equipment = request.POST.get('equipment', '')
            category = request.POST.get('category', 'standard')
            selected_equipment = _resolve_selected_equipment(request.POST.get('equipment_ids'), category)
            if selected_equipment:
                equipment = '\n'.join(item.name for item in selected_equipment)
            primary_image, extra_images = _extract_room_image_uploads(request)

            _validate_room_image_limit(
                room=Room(),
                primary_image=primary_image,
                extra_images=extra_images,
            )

            # 👉 получаем выбранный офис
            office_id = request.POST.get('office')

            room = Room.objects.create(
                name=name,
                location=location,
                capacity=capacity,
                price_per_hour=price_per_hour,
                equipment=equipment,
                category=category,
                office_id=office_id if office_id else None,  # ← ВАЖНО!
                is_active=True
            )
            office_id = request.POST.get("office")
            if office_id:
                room.office_id = office_id

            room.save()

            if selected_equipment:
                room.equipment_items.set(selected_equipment)

            if primary_image:
                room.image = _save_room_image_file(primary_image)
                room.save(update_fields=['image'])

            _append_room_gallery_images(room, extra_images)

            messages.success(request, '✅ Комната успешно добавлена!')
            return JsonResponse({'success': True, 'room_id': room.id})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})


@login_required
def edit_room(request, room_id):
    """Редактирование комнаты - админ и менеджер"""
    if not _has_management_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен!'})

    try:
        room = Room.objects.prefetch_related('gallery_images').get(id=room_id)

        if request.method == 'POST':
            # Админ может менять всё, менеджер только цену и оборудование
            if _has_admin_access(request.user):
                room.name = request.POST.get('name', room.name)
                room.location = request.POST.get('location', room.location)
                office_id = request.POST.get("office")
                room.office_id = office_id if office_id else None
                room.capacity = request.POST.get('capacity', room.capacity)
                room.category = request.POST.get('category', room.category)

            room.price_per_hour = request.POST.get('price_per_hour', room.price_per_hour)
            selected_equipment = None
            submitted_equipment_ids = request.POST.get('equipment_ids')
            if submitted_equipment_ids is not None:
                selected_equipment = _resolve_selected_equipment(submitted_equipment_ids, room.category)
                room.equipment = '\n'.join(item.name for item in selected_equipment)
            else:
                room.equipment = request.POST.get('equipment', room.equipment)

            # Обработка изображения (только админ)
            if _has_admin_access(request.user):
                primary_image, extra_images = _extract_room_image_uploads(request, allow_gallery_fallback=False)
                removed_gallery_ids = _parse_gallery_image_ids(request.POST.getlist('remove_gallery_image_ids'))
                selected_gallery_cover_id = _parse_optional_int(request.POST.get('selected_gallery_cover_id'))
                ordered_gallery_ids = _parse_gallery_order(request.POST.get('gallery_order'))

                if selected_gallery_cover_id in removed_gallery_ids:
                    removed_gallery_ids = [image_id for image_id in removed_gallery_ids if image_id != selected_gallery_cover_id]

                _validate_room_image_limit(
                    room=room,
                    primary_image=primary_image,
                    extra_images=extra_images,
                    removed_gallery_ids=removed_gallery_ids,
                )

                if primary_image:
                    room.image = _save_room_image_file(primary_image)
                    selected_gallery_cover_id = None

            room.save()

            if selected_equipment is not None:
                room.equipment_items.set(selected_equipment)

            if _has_admin_access(request.user):
                if selected_gallery_cover_id and not primary_image:
                    if removed_gallery_ids:
                        room.gallery_images.filter(id__in=removed_gallery_ids).delete()

                    _apply_room_gallery_order(room, ordered_gallery_ids)
                    _promote_gallery_image_to_cover(room, selected_gallery_cover_id)
                else:
                    if removed_gallery_ids:
                        room.gallery_images.filter(id__in=removed_gallery_ids).delete()

                    _apply_room_gallery_order(room, ordered_gallery_ids)

                _append_room_gallery_images(room, extra_images)

            messages.success(request, '✅ Комната успешно обновлена!')
            return JsonResponse({'success': True})

    except Room.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Комната не найдена'})
    except ValueError as error:
        return JsonResponse({'success': False, 'error': str(error)})

    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})


@login_required
def get_all_rooms(request):
    """Получить все комнаты для управления"""
    if not _has_management_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен'})

    rooms = Room.objects.all()
    rooms_data = []
    for room in rooms:
        rooms_data.append({
            'id': room.id,
            'name': room.name,
            'location': room.location,
            'capacity': room.capacity,
            'price_per_hour': str(room.price_per_hour),
            'equipment': room.equipment,
            'image': room.image.url if room.image else None,
            'image_count': (1 if room.image else 0) + room.gallery_images.count(),
        })

    return JsonResponse({'rooms': rooms_data})


@login_required
def get_room_data(request, room_id):
    """Получить данные комнаты для редактирования"""
    try:
        room = Room.objects.select_related('office').prefetch_related('gallery_images', 'equipment_items').get(id=room_id)
        return JsonResponse({
            'success': True,
            'room': {
                'id': room.id,
                'name': room.name,
                'location': room.location,
                'category': room.category,
                "office_id": room.office.id if room.office else None,
                'capacity': room.capacity,
                'price_per_hour': str(room.price_per_hour),
                'equipment': room.equipment,
                'equipment_ids': list(room.equipment_items.values_list('id', flat=True)),
                'image': room.image.url if room.image else None,
                'gallery_images': _build_room_gallery_payload(room),
                'image_limit': Room.MAX_TOTAL_IMAGES,
                'image_count': (1 if room.image else 0) + room.gallery_images.count(),
            }
        })
    except Room.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Комната не найдена'})


@login_required
def delete_room(request, room_id):
    """Удаление комнаты - только админ"""
    if not _has_admin_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен!'})

    try:
        room = Room.objects.get(id=room_id)
        room.delete()
        messages.success(request, '✅ Комната успешно удалена!')
        return JsonResponse({'success': True})
    except Room.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Комната не найдена'})


@login_required
def change_password(request):
    """Изменение пароля с валидацией Django"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(old_password):
            messages.error(request, '❌ Старый пароль неверен!')
            return redirect('profile')

        if new_password != confirm_password:
            messages.error(request, '❌ Пароли не совпадают!')
            return redirect('profile')

        try:
            # 🔐 ВСТРОЕННАЯ ВАЛИДАЦИЯ DJANGO
            validate_password(new_password, user=request.user)

            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)

            messages.success(request, '🔐 Пароль успешно изменён!')
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, f'❌ {error}')

        return redirect('profile')


@login_required
def room_management_main(request):
    """Главная страница управления комнатами - выбор категории"""
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('home')

    # Считаем комнаты по категориям
    categories = {
        'economy': Room.objects.filter(category='economy').count(),
        'standard': Room.objects.filter(category='standard').count(),
        'comfort': Room.objects.filter(category='comfort').count(),
        'vip': Room.objects.filter(category='vip').count(),
        'luxury': Room.objects.filter(category='luxury').count(),
    }

    equipment_catalog = _serialize_equipment_catalog()

    return render(request, 'room_management_main.html', {
        'categories': categories,
        'equipment_catalog': equipment_catalog,
        'room_category_choices': Room.CATEGORY_CHOICES,
    })


@login_required
def room_management_category(request, category):
    """Страница управления комнатами конкретной категории"""
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('home')

    # Проверяем валидность категории
    valid_categories = ['economy', 'standard', 'comfort', 'vip', 'luxury']
    if category not in valid_categories:
        messages.error(request, '❌ Неверная категория!')
        return redirect('room_management_main')

    rooms = Room.objects.filter(category=category)
    category_display = dict(Room.CATEGORY_CHOICES)[category]

    # 👉 офисы
    offices = Office.objects.all()

    # ✅ ДОБАВЛЕНО: диапазоны вместимости
    CAPACITY_RANGES = {
        'economy': range(1, 7),
        'standard': range(5, 9),
        'comfort': range(7, 11),
        'vip': range(9, 13),
        'luxury': range(11, 17),
    }

    capacity_range = CAPACITY_RANGES.get(category, [])
    equipment_catalog = _serialize_equipment_catalog()

    return render(request, 'room_management_category.html', {
        'rooms': rooms,
        'category': category,
        'category_display': category_display,
        'offices': offices,
        'capacity_range': capacity_range,  # ✅ ВОТ ОНО
        'equipment_catalog': equipment_catalog,
        'room_category_choices': Room.CATEGORY_CHOICES,
    })


@login_required
def equipment_management(request):
    if not _has_admin_access(request.user):
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('home')

    equipment_items = Equipment.objects.all().annotate(rooms_count=Count('rooms')).order_by('name')

    return render(request, 'equipment_management.html', {
        'equipment_catalog': _serialize_equipment_catalog(equipment_items),
        'room_category_choices': Room.CATEGORY_CHOICES,
    })


@login_required
def add_equipment(request):
    if not _has_admin_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен!'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

    name = (request.POST.get('name') or '').strip()
    categories = [category for category in request.POST.getlist('categories') if category]

    if not name:
        return JsonResponse({'success': False, 'error': 'Название оборудования обязательно.'})

    valid_categories = {category for category, _ in Room.CATEGORY_CHOICES}
    if any(category not in valid_categories for category in categories):
        return JsonResponse({'success': False, 'error': 'Указана неверная категория оборудования.'})

    if Equipment.objects.filter(name__iexact=name).exists():
        return JsonResponse({'success': False, 'error': 'Такое оборудование уже существует.'})

    equipment = Equipment.objects.create(name=name, categories=categories, is_active=True)
    return JsonResponse({'success': True, 'equipment': _serialize_equipment_catalog([equipment])[0]})


@login_required
def edit_equipment(request, equipment_id):
    if not _has_admin_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен!'})

    try:
        equipment = Equipment.objects.get(id=equipment_id)
    except Equipment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Оборудование не найдено.'})

    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'equipment': _serialize_equipment_catalog([equipment])[0]
        })

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

    name = (request.POST.get('name') or '').strip()
    categories = [category for category in request.POST.getlist('categories') if category]
    valid_categories = {category for category, _ in Room.CATEGORY_CHOICES}

    if not name:
        return JsonResponse({'success': False, 'error': 'Название оборудования обязательно.'})

    if any(category not in valid_categories for category in categories):
        return JsonResponse({'success': False, 'error': 'Указана неверная категория оборудования.'})

    if Equipment.objects.filter(name__iexact=name).exclude(id=equipment.id).exists():
        return JsonResponse({'success': False, 'error': 'Такое оборудование уже существует.'})

    equipment.name = name
    equipment.categories = categories
    equipment.save(update_fields=['name', 'categories'])
    _sync_rooms_equipment(list(equipment.rooms.values_list('id', flat=True)))

    return JsonResponse({
        'success': True,
        'equipment': _serialize_equipment_catalog([equipment])[0]
    })


@login_required
def delete_equipment(request, equipment_id):
    if not _has_admin_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен!'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

    try:
        equipment = Equipment.objects.get(id=equipment_id)
    except Equipment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Оборудование не найдено.'})

    related_room_ids = list(equipment.rooms.values_list('id', flat=True))
    equipment.delete()
    _sync_rooms_equipment(related_room_ids)

    return JsonResponse({'success': True})


@login_required
def toggle_room_status(request, room_id):
    """Переключение статуса комнаты (активна/скрыта)"""
    if not _has_admin_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен!'})

    try:
        room = Room.objects.get(id=room_id)
        # Переключаем между активной и скрытой
        if room.status == 'active':
            room.status = 'hidden'
        else:
            room.status = 'active'
        room.save()

        return JsonResponse({'success': True, 'new_status': room.status})
    except Room.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Комната не найдена'})


@login_required
def delete_user(request, user_id):
    """Удаление пользователя (только для админа)"""
    if not _has_admin_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен!'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

    try:
        user_to_delete = User.objects.get(id=user_id)
        policy = _build_admin_user_policy(
            actor=request.user,
            target_user=user_to_delete,
            activity_snapshot=_build_user_activity_maps([user_to_delete.id]).get(user_to_delete.id, {}),
            admin_count=User.objects.filter(role='admin').count(),
        )

        if not policy['can_delete']:
            return JsonResponse({'success': False, 'error': policy['delete_reason']})

        user_to_delete.delete()
        return JsonResponse({'success': True})

    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Пользователь не найден'})


@login_required
def booking_history(request):
    """История бронирований - ВСЕГДА только СВОИ бронирования"""
    # Получаем бронирования пользователя
    user_bookings = Booking.objects.filter(user=request.user).order_by('-created_at')

    # ★★★ ДОБАВЛЯЕМ СТАТИСТИКУ ★★★
    bookings_count = user_bookings.count()
    active_bookings_count = user_bookings.filter(status__in=['pending', 'confirmed']).count()
    completed_bookings_count = user_bookings.filter(status='completed').count()
    cancelled_bookings_count = user_bookings.filter(status='cancelled').count()

    return render(request, 'booking_history.html', {
        'bookings': user_bookings,
        'bookings_count': bookings_count,
        'active_bookings_count': active_bookings_count,
        'completed_bookings_count': completed_bookings_count,
        'cancelled_bookings_count': cancelled_bookings_count
    })


def offices_view(request):
    """Страница с офисами и картами"""
    offices = Office.objects.filter(is_active=True)
    return render(request, 'offices.html', {'offices': offices})


@login_required
def office_management(request):
    """Управление офисами для админа"""
    if not _has_admin_access(request.user):  # ← ИЗМЕНИЛ НА ТОТ ЖЕ СТАНДАРТ
        messages.error(request, '❌ Доступ запрещен!')
        return redirect('home')

    offices = Office.objects.all()
    return render(request, 'office_management.html', {'offices': offices})


@login_required
def edit_office(request, office_id):
    if not _has_admin_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен!'})

    try:
        office = Office.objects.get(id=office_id)

        if request.method == 'POST':
            office.name = request.POST.get('name')
            office.address = request.POST.get('address')
            office.phone = request.POST.get('phone')
            office.work_hours = request.POST.get('work_hours')
            office.latitude = request.POST.get('latitude')
            office.longitude = request.POST.get('longitude')
            office.yandex_map_url = request.POST.get('yandex_map_url')
            office.parking = request.POST.get('parking')
            office.transport = request.POST.get('transport')
            office.amenities = request.POST.get('amenities')
            # ★★★ УБЕРИ ЭТУ СТРОКУ ★★★
            # office.marker_text = request.POST.get('marker_text', 'Офис')
            office.is_active = True

            office.save()
            messages.success(request, '✅ Офис успешно обновлен!')
            return JsonResponse({'success': True})

        return JsonResponse({
            'success': True,
            'office': {
                'id': office.id,
                'name': office.name,
                'address': office.address,
                'phone': office.phone,
                'work_hours': office.work_hours,
                'latitude': office.latitude,
                'longitude': office.longitude,
                'yandex_map_url': office.yandex_map_url,
                'parking': office.parking,
                'transport': office.transport,
                'amenities': office.amenities,
                # ★★★ УБЕРИ ЭТО ПОЛЕ ИЗ ОТВЕТА ★★★
                # 'marker_text': office.marker_text,
                'is_active': office.is_active,
            }
        })

    except Office.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Офис не найден'})


@login_required
def add_office(request):
    if not _has_admin_access(request.user):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен!'})

    if request.method == 'POST':
        try:
            office = Office.objects.create(
                name=request.POST.get('name'),
                address=request.POST.get('address'),
                phone=request.POST.get('phone'),
                work_hours=request.POST.get('work_hours'),
                latitude=request.POST.get('latitude'),
                longitude=request.POST.get('longitude'),
                yandex_map_url=request.POST.get('yandex_map_url'),
                parking=request.POST.get('parking'),
                transport=request.POST.get('transport'),
                amenities=request.POST.get('amenities'),
                marker_text=request.POST.get('marker_text', 'Офис'),
                is_active=True  # ★★★ ВСЕГДА TRUE ★★★
            )

            messages.success(request, '✅ Офис успешно добавлен!')
            return JsonResponse({'success': True, 'office_id': office.id})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})


@login_required
def delete_office(request, office_id):
    """Удаление офиса"""
    if not _has_admin_access(request.user):  # ← ИЗМЕНИЛ НА ТОТ ЖЕ СТАНДАРТ
        return JsonResponse({'success': False, 'error': 'Доступ запрещен!'})

    try:
        office = Office.objects.get(id=office_id)
        office.delete()
        messages.success(request, '✅ Офис успешно удален!')
        return JsonResponse({'success': True})
    except Office.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Офис не найден'})


@login_required
def database_backup_view(request):
    """Страница управления резервными копиями БД"""
    if not _has_admin_access(request.user):
        messages.error(request, 'Доступ запрещен! Только для администраторов.')
        return redirect('home')

    # Временное решение - читаем бэкапы из папки
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    backups = []
    if os.path.exists(backup_dir):
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(backup_dir, filename)
                file_size = os.path.getsize(file_path)
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))

                backups.append({
                    'id': filename,
                    'filename': filename,
                    'created_at': file_time,
                    'size': format_file_size(file_size),
                })

    # Сортируем по дате создания (новые первыми)
    backups.sort(key=lambda x: x['created_at'], reverse=True)

    # Импортируем модели внутри функции
    from .models import User, Booking, Room, Review

    # Статистика базы данных
    stats = {
        'users': User.objects.count(),
        'bookings': Booking.objects.count(),
        'rooms': Room.objects.count(),
        'reviews': Review.objects.count(),
        'offices': Office.objects.count(),
        'support_tickets': SupportTicket.objects.count(),
        'ticket_responses': TicketResponse.objects.count(),
    }

    return render(request, 'database_backup.html', {
        'backups': backups,
        'stats': stats,
    })


@login_required
def create_backup(request):
    """Создание резервной копии базы данных"""
    if not _has_admin_access(request.user):
        messages.error(request, 'Доступ запрещен!')
        return redirect('home')

    if request.method != 'POST':
        return redirect('database_backup')

    try:
        # Импортируем модели внутри функции
        from .models import User, Booking, Room, Review, Office

        # Создаем директорию для бэкапов
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        # Генерируем имя файла с текущей датой и временем
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{timestamp}.json'
        file_path = os.path.join(backup_dir, filename)

        # Собираем данные из всех таблиц
        backup_data = {
            'created_at': datetime.now().isoformat(),
            'created_by': request.user.username,
            'data': {
                'users': list(User.objects.values()),
                'rooms': list(Room.objects.values()),
                'bookings': list(Booking.objects.values()),
                'reviews': list(Review.objects.values()),
                'offices': list(Office.objects.values()),
                'support_tickets': list(SupportTicket.objects.values()),
                'ticket_responses': list(TicketResponse.objects.values()),
            }
        }

        # Сохраняем в JSON файл
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)

        messages.success(request, f'Резервная копия успешно создана: {filename}')
    except Exception as e:
        messages.error(request, f'Ошибка при создании резервной копии: {str(e)}')

    return redirect('database_backup')


@login_required
def download_backup(request, backup_id):
    """Скачивание резервной копии"""
    if not _has_admin_access(request.user):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)

    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    file_path = os.path.join(backup_dir, backup_id)

    # Проверяем что файл существует и находится в папке backups
    if not os.path.exists(file_path) or not file_path.startswith(backup_dir):
        raise Http404('Файл не найден')

    # Отправляем файл на скачивание
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{backup_id}"'
        return response


@login_required
def delete_backup(request, backup_id):
    """Удаление резервной копии"""
    if not _has_admin_access(request.user):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)

    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    file_path = os.path.join(backup_dir, backup_id)

    # Проверяем что файл существует и находится в папке backups
    if not os.path.exists(file_path) or not file_path.startswith(backup_dir):
        return JsonResponse({'error': 'Файл не найден'}, status=404)

    try:
        os.remove(file_path)
        return JsonResponse({'success': True, 'message': 'Резервная копия удалена'})
    except Exception as e:
        return JsonResponse({'error': f'Ошибка при удалении: {str(e)}'}, status=500)


@login_required
def export_json_backup(request):
    """Экспорт всех данных в JSON"""
    if not _has_admin_access(request.user):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)

    try:
        # Импортируем модели внутри функции
        from .models import User, Booking, Room, Review, Office

        # Собираем данные из всех таблиц
        backup_data = {
            'created_at': datetime.now().isoformat(),
            'created_by': request.user.username,
            'data': {
                'users': list(User.objects.values()),
                'rooms': list(Room.objects.values()),
                'bookings': list(Booking.objects.values()),
                'reviews': list(Review.objects.values()),
                'offices': list(Office.objects.values()),
            }
        }

        # Генерируем имя файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_export_{timestamp}.json'

        # Отправляем как скачиваемый файл
        response = HttpResponse(
            json.dumps(backup_data, ensure_ascii=False, indent=2, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return JsonResponse({'error': f'Ошибка при экспорте: {str(e)}'}, status=500)


def format_file_size(size_bytes):
    """Форматирование размера файла"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} ТБ"

@login_required
def change_user_role(request, user_id):
    """Смена роли пользователя — только для админов"""
    if not _has_admin_access(request.user):
        return JsonResponse({'success': False, 'error': 'Нет прав'}, status=403)

    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Неверный метод'}, status=400)

    new_role = request.POST.get("role")
    if new_role not in ['owner', 'admin', 'manager', 'user']:
        return JsonResponse({'success': False, 'error': 'Неверная роль'}, status=400)

    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
        policy = _build_admin_user_policy(
            actor=request.user,
            target_user=user,
            activity_snapshot=_build_user_activity_maps([user.id]).get(user.id, {}),
            admin_count=User.objects.filter(role='admin').count(),
        )

        if not policy['can_change_role']:
            return JsonResponse({'success': False, 'error': policy['role_change_reason']}, status=400)

        if new_role not in policy['allowed_roles']:
            return JsonResponse({'success': False, 'error': 'Эту роль нельзя назначить выбранному пользователю.'}, status=400)

        if new_role == 'owner':
            owner_count = User.objects.filter(role='owner').exclude(id=user.id).count()
            if user.id == request.user.id and getattr(request.user, 'role', None) == 'admin' and owner_count == 0:
                user.role = 'owner'
                user.save(update_fields=['role'])
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Назначить владельца можно только самому себе и только если владельца еще нет.',
                }, status=400)
        else:
            user.role = new_role
            user.save(update_fields=['role'])

        return JsonResponse({'success': True})

    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
