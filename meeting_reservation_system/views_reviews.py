from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Review, ReviewReply, Room
import json
import re

PROFANITY_LIST = [
    # Основные матерные слова и их вариации
    'хуй', 'хуя', 'хуе', 'хую', 'хуи', 'хуём', 'хуёв', 'хуев', 'хуйн', 'хуйл', 'хуйс',
    'пизд', 'пезд', 'пиздец', 'пизда', 'пизду', 'пизды', 'пиздат', 'пиздос', 'пиздюк',
    'блядь', 'бляд', 'блять', 'блят', 'бля', 'блядин', 'блядск', 'блядств',
    'ебать', 'ебан', 'ебат', 'ебёт', 'ебет', 'ебал', 'ебло', 'ебну', 'ебут', 'ебуч', 'ёб', 'еб',
    'сука', 'суки', 'сучк', 'сучар', 'сучий', 'сученый',
    'мудак', 'мудил', 'мудо', 'муда',
    'залуп', 'залупа', 'залупин',
    'дрочи', 'дроч', 'дрочк', 'дрочер',
    'шлюх', 'шлюшк', 'шалав',
    'пидор', 'пидар', 'пидр', 'педик', 'педрил',
    'гандон', 'гондон', 'кондом',
    'жопа', 'жоп', 'жопн', 'жопор',
    'срать', 'срал', 'сран', 'засран', 'высрал', 'насрал', 'о��осрал', 'усрал',
    'говно', 'говн', 'гавно', 'гавён',
    'уебан', 'уёбок', 'уебок', 'уебищ', 'уёбищ',
    'долбоёб', 'долбоеб', 'долбаёб', 'долбаеб',
    'заеб', 'заёб', 'заебал', 'заебис', 'заебат', 'заёбыв',
    'выеб', 'выёб', 'поеб', 'поёб', 'наеб', 'наёб', 'объеб', 'объёб',
    'отъеб', 'отъёб', 'подъеб', 'подъёб', 'разъеб', 'разъёб',
    'ёбан', 'ебан', 'ебён', 'ебен', 'ёбнут', 'ебнут',
    'хер', 'херн', 'херов', 'похер', 'нахер', 'охерел', 'охуел', 'охуе', 'охере',
    'писюн', 'писюк', 'пися', 'письк',
    'член', 'членос',
    'трах', 'трахну', 'трахал', 'трахать',
    # Замаскированные вариации
    'х*й', 'п*зд', 'б*я', 'е*ать', 'с*ка', 'п*дор', 'г*вно', 'ж*па',
    'xyй', 'пuзд', 'бляtь', 'eбать', 'cyкa', 'хyй', 'пиzdа',
    # Транслит вариации
    'hui', 'huy', 'pizd', 'blyad', 'blya', 'ebat', 'suka', 'mudak', 'pidor', 'govno',
    'fuck', 'fucking', 'shit', 'bitch', 'asshole', 'bastard', 'dick', 'cock', 'pussy', 'cunt',
    'whore', 'slut', 'nigger', 'nigga', 'faggot', 'fag',
]


def contains_profanity(text):
    """Проверяет текст на наличие нецензурной лексики"""
    text_lower = text.lower()

    # Убираем пробелы между буквами (обход типа "х у й")
    text_no_spaces = re.sub(r'\s+', '', text_lower)

    # Заменяем похожие символы на буквы
    replacements = {
        '0': 'о', 'o': 'о', '3': 'з', 'e': 'е', 'a': 'а', '@': 'а',
        '1': 'и', 'i': 'и', 'u': 'у', 'y': 'у', 'x': 'х', 'c': 'с',
        'k': 'к', 'p': 'р', 'b': 'б', 'n': 'н', 'm': 'м', 'd': 'д',
        '4': 'ч', '6': 'б', '9': 'д',
    }

    normalized_text = text_no_spaces
    for eng, rus in replacements.items():
        normalized_text = normalized_text.replace(eng, rus)

    # Проверяем оба варианта текста
    for word in PROFANITY_LIST:
        if word in text_lower or word in text_no_spaces or word in normalized_text:
            return True

    return False


@login_required
def add_review(request, room_id):
    """Добавление отзыва к комнате"""
    if request.method == 'POST':
        room = get_object_or_404(Room, id=room_id)

        # Проверяем, есть ли уже отзыв от этого пользователя
        existing_review = Review.objects.filter(user=request.user, room=room).first()
        if existing_review:
            return JsonResponse({
                'success': False,
                'error': 'Вы уже оставили отзыв на эту комнату. Вы можете отредактировать его.'
            })

        try:
            data = json.loads(request.body)
            rating = int(data.get('rating', 0))
            text = data.get('text', '').strip()

            if not (1 <= rating <= 5):
                return JsonResponse({'success': False, 'error': 'Оценка должна быть от 1 до 5'})

            if len(text) < 10:
                return JsonResponse({'success': False, 'error': 'Отзыв должен содержать минимум 10 символов'})

            if contains_profanity(text):
                return JsonResponse({
                    'success': False,
                    'error': 'Отзыв содержит нецензурную лексику. Пожалуйста, перефразируйте ваш отзыв.'
                })

            review = Review.objects.create(
                user=request.user,
                room=room,
                rating=rating,
                text=text,
                status='pending'  # Отзыв на модерации
            )

            return JsonResponse({
                'success': True,
                'message': 'Отзыв отправлен на модерацию!'
            })

        except (json.JSONDecodeError, ValueError) as e:
            return JsonResponse({'success': False, 'error': 'Некорректные данные'})

    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'})


@login_required
def edit_review(request, review_id):
    """Редактирование отзыва"""
    review = get_object_or_404(Review, id=review_id, user=request.user)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rating = int(data.get('rating', 0))
            text = data.get('text', '').strip()

            if not (1 <= rating <= 5):
                return JsonResponse({'success': False, 'error': 'Оценка должна быть от 1 до 5'})

            if len(text) < 10:
                return JsonResponse({'success': False, 'error': 'Отзыв должен содержать минимум 10 символов'})

            if contains_profanity(text):
                return JsonResponse({
                    'success': False,
                    'error': 'Отзыв содержит нецензурную лексику. Пожалуйста, перефразируйте ваш отзыв.'
                })

            review.rating = rating
            review.text = text
            review.status = 'pending'  # Снова на модерацию после редактирования
            review.save()

            return JsonResponse({
                'success': True,
                'message': 'Отзыв обновлен и отправлен на повторную модерацию!'
            })

        except (json.JSONDecodeError, ValueError) as e:
            return JsonResponse({'success': False, 'error': 'Некорректные данные'})

    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'})


@login_required
def delete_review(request, review_id):
    """Удаление отзыва пользователем"""
    review = get_object_or_404(Review, id=review_id, user=request.user)

    if request.method == 'POST':
        review.delete()
        return JsonResponse({'success': True, 'message': 'Отзыв удален!'})

    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'})


@login_required
@require_POST
def admin_delete_review(request, review_id):
    """Удаление отзыва админом/менеджером"""
    if request.user.role not in ['admin', 'manager']:
        return JsonResponse({'success': False, 'error': 'Доступ запрещен'})

    review = get_object_or_404(Review, id=review_id)
    review.delete()

    return JsonResponse({'success': True, 'message': 'Отзыв удален!'})


@login_required
@require_POST
def reply_to_review(request, review_id):
    """Ответ на отзыв от админа/менеджера"""
    if request.user.role not in ['admin', 'manager']:
        return JsonResponse({'success': False, 'error': 'Доступ запрещен'})

    review = get_object_or_404(Review, id=review_id)

    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()

        if len(text) < 5:
            return JsonResponse({'success': False, 'error': 'Ответ должен содержать минимум 5 символов'})

        reply = ReviewReply.objects.create(
            review=review,
            user=request.user,
            text=text
        )

        return JsonResponse({
            'success': True,
            'message': 'Ответ добавлен!',
            'reply': {
                'id': reply.id,
                'username': reply.user.username,
                'role': reply.user.get_role_display(),
                'text': reply.text,
                'created_at': reply.created_at.strftime('%d.%m.%Y %H:%M')
            }
        })

    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Некорректные данные'})


@login_required
@require_POST
def delete_reply(request, reply_id):
    """Удаление ответа на отзыв"""
    if request.user.role not in ['admin', 'manager']:
        return JsonResponse({'success': False, 'error': 'Доступ запрещен'})

    reply = get_object_or_404(ReviewReply, id=reply_id)
    reply.delete()

    return JsonResponse({'success': True, 'message': 'Ответ удален!'})


def get_room_reviews(request, room_id):
    """Получение одобренных отзывов комнаты"""
    room = get_object_or_404(Room, id=room_id)

    # Получаем только одобренные отзывы
    reviews = Review.objects.filter(room=room, status='approved').select_related('user').prefetch_related('replies',
                                                                                                          'replies__user')

    # Проверяем, есть ли у текущего пользователя отзыв на эту комнату
    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(room=room, user=request.user).first()

    is_admin_or_manager = request.user.is_authenticated and request.user.role in ['admin', 'manager']

    reviews_data = []
    for review in reviews:
        replies_data = []
        for reply in review.replies.all():
            replies_data.append({
                'id': reply.id,
                'username': reply.user.username,
                'role': reply.user.get_role_display(),
                'text': reply.text,
                'created_at': reply.created_at.strftime('%d.%m.%Y %H:%M')
            })

        reviews_data.append({
            'id': review.id,
            'username': review.user.username,
            'avatar': review.user.avatar.url if review.user.avatar else None,
            'rating': review.rating,
            'text': review.text,
            'created_at': review.created_at.strftime('%d.%m.%Y %H:%M'),
            'is_owner': request.user.is_authenticated and review.user == request.user,
            'replies': replies_data  # Добавлены ответы
        })

    user_review_data = None
    if user_review:
        user_review_data = {
            'id': user_review.id,
            'rating': user_review.rating,
            'text': user_review.text,
            'status': user_review.status,
            'status_display': user_review.get_status_display(),
            'created_at': user_review.created_at.strftime('%d.%m.%Y %H:%M'),
        }

    # Средний рейтинг
    avg_rating = 0
    if reviews:
        avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1)

    return JsonResponse({
        'reviews': reviews_data,
        'user_review': user_review_data,
        'total_count': len(reviews_data),
        'avg_rating': avg_rating,
        'is_admin_or_manager': is_admin_or_manager  # Флаг для UI
    })


@login_required
def review_moderation(request):
    """Страница модерации отзывов (для админа/менеджера)"""
    if request.user.role not in ['admin', 'manager']:
        messages.error(request, 'Доступ запрещен!')
        return redirect('home')

    # Получаем отзывы на модерации
    pending_reviews = Review.objects.filter(status='pending').select_related('user', 'room').order_by('-created_at')

    return render(request, 'review_moderation.html', {
        'pending_reviews': pending_reviews
    })


@login_required
def all_reviews(request):
    """Страница всех одобренных отзывов (для админа/менеджера)"""
    if request.user.role not in ['admin', 'manager']:
        messages.error(request, 'Доступ запрещен!')
        return redirect('home')

    # Получаем все одобренные отзывы
    reviews = Review.objects.filter(status='approved').select_related('user', 'room').prefetch_related('replies',
                                                                                                       'replies__user').order_by(
        '-created_at')

    # Получаем все комнаты для фильтрации
    rooms = Room.objects.filter(is_active=True).order_by('name')

    # Статистика
    total_count = reviews.count()
    avg_rating = 0
    if total_count > 0:
        avg_rating = round(sum(r.rating for r in reviews) / total_count, 1)

    rooms_stats = {}
    for room in rooms:
        room_reviews = reviews.filter(room=room)
        room_count = room_reviews.count()
        room_avg = 0
        if room_count > 0:
            room_avg = round(sum(r.rating for r in room_reviews) / room_count, 1)
        rooms_stats[room.id] = {
            'count': room_count,
            'avg_rating': room_avg
        }

    return render(request, 'all_reviews.html', {
        'reviews': reviews,
        'rooms': rooms,
        'total_count': total_count,
        'avg_rating': avg_rating,
        'rooms_stats': json.dumps(rooms_stats),  # JSON для JS
    })


@login_required
@require_POST
def approve_review(request, review_id):
    """Одобрение отзыва"""
    if request.user.role not in ['admin', 'manager']:
        return JsonResponse({'success': False, 'error': 'Доступ запрещен'})

    review = get_object_or_404(Review, id=review_id)
    review.status = 'approved'
    review.save()

    return JsonResponse({'success': True, 'message': 'Отзыв одобрен!'})


@login_required
@require_POST
def reject_review(request, review_id):
    """Отклонение (удаление) отзыва"""
    if request.user.role not in ['admin', 'manager']:
        return JsonResponse({'success': False, 'error': 'Доступ запрещен'})

    review = get_object_or_404(Review, id=review_id)
    review.delete()

    return JsonResponse({'success': True, 'message': 'Отзыв отклонен и удален!'})


def get_user_reviews(request):
    """Получение всех отзывов пользователя для профиля"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Требуется авторизация'})

    reviews = Review.objects.filter(user=request.user).select_related('room').order_by('-created_at')

    reviews_data = []
    for review in reviews:
        reviews_data.append({
            'id': review.id,
            'room_id': review.room.id,
            'room_name': review.room.name,
            'room_category': review.room.category,
            'rating': review.rating,
            'text': review.text,
            'status': review.status,
            'status_display': review.get_status_display(),
            'created_at': review.created_at.strftime('%d.%m.%Y'),
            'time': review.created_at.strftime('%H:%M'),
        })

    return JsonResponse({
        'success': True,
        'reviews': reviews_data
    })


@login_required
def my_reviews_page(request):
    """Страница со всеми отзывами пользователя"""
    reviews = Review.objects.filter(user=request.user).select_related('room').order_by('-created_at')

    # Статистика
    total_count = reviews.count()
    approved_count = reviews.filter(status='approved').count()
    pending_count = reviews.filter(status='pending').count()
    rejected_count = reviews.filter(status='rejected').count()

    return render(request, 'my_reviews.html', {
        'reviews': reviews,
        'total_count': total_count,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
    })
