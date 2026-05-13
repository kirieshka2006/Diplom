from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from meeting_reservation_system.models import (
    Booking,
    FAQ,
    FAQCategory,
    InfoSection,
    Office,
    Review,
    ReviewReply,
    Room,
    SupportTicket,
    TicketResponse,
    User,
)


DEMO_PASSWORD = "DemoPass123!"


class Command(BaseCommand):
    help = "Заполняет локальную базу демонстрационными данными для удобной проверки интерфейса"

    def handle(self, *args, **options):
        with transaction.atomic():
            users = self._seed_users()
            offices = self._seed_offices()
            rooms = self._seed_rooms(offices)
            self._seed_faq_categories()
            self._seed_info_sections()
            self._seed_faq()
            self._seed_bookings(users, rooms)
            self._seed_reviews(users, rooms)
            self._seed_tickets(users)

        self.stdout.write(self.style.SUCCESS("✅ Demo-данные успешно загружены"))
        self.stdout.write("")
        self.stdout.write("Тестовые учётные записи:")
        self.stdout.write(f"  admin_demo / {DEMO_PASSWORD}")
        self.stdout.write(f"  manager_demo / {DEMO_PASSWORD}")
        self.stdout.write(f"  demo_anna / {DEMO_PASSWORD}")
        self.stdout.write(f"  demo_ivan / {DEMO_PASSWORD}")
        self.stdout.write(f"  demo_olga / {DEMO_PASSWORD}")

    def _seed_users(self):
        avatar_path = Path(settings.MEDIA_ROOT) / "avatars" / "lamp.jpeg"
        avatar_value = "avatars/lamp.jpeg" if avatar_path.exists() else None

        users = {
            "admin_demo": self._upsert_user(
                username="admin_demo",
                email="admin_demo@example.com",
                role="admin",
                first_name="Алексей",
                last_name="Орлов",
                patronymic="Сергеевич",
                phone="+7 (950) 100-10-10",
                gender="M",
                is_staff=True,
                is_superuser=True,
                email_verified=True,
                avatar=avatar_value,
            ),
            "manager_demo": self._upsert_user(
                username="manager_demo",
                email="manager_demo@example.com",
                role="manager",
                first_name="Марина",
                last_name="Котова",
                patronymic="Ильинична",
                phone="+7 (950) 200-20-20",
                gender="F",
                is_staff=True,
                is_superuser=False,
                email_verified=True,
                avatar=avatar_value,
            ),
            "demo_anna": self._upsert_user(
                username="demo_anna",
                email="anna_demo@example.com",
                role="user",
                first_name="Анна",
                last_name="Лебедева",
                patronymic="Андреевна",
                phone="+7 (950) 300-30-30",
                gender="F",
                is_staff=False,
                is_superuser=False,
                email_verified=True,
                avatar=avatar_value,
            ),
            "demo_ivan": self._upsert_user(
                username="demo_ivan",
                email="ivan_demo@example.com",
                role="user",
                first_name="Иван",
                last_name="Мельников",
                patronymic="Олегович",
                phone="+7 (950) 400-40-40",
                gender="M",
                is_staff=False,
                is_superuser=False,
                email_verified=True,
                avatar=None,
            ),
            "demo_olga": self._upsert_user(
                username="demo_olga",
                email="olga_demo@example.com",
                role="user",
                first_name="Ольга",
                last_name="Соколова",
                patronymic="Викторовна",
                phone="+7 (950) 500-50-50",
                gender="F",
                is_staff=False,
                is_superuser=False,
                email_verified=True,
                avatar=None,
            ),
        }
        return users

    def _upsert_user(
        self,
        *,
        username,
        email,
        role,
        first_name,
        last_name,
        patronymic,
        phone,
        gender,
        is_staff,
        is_superuser,
        email_verified,
        avatar,
    ):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "role": role,
                "first_name": first_name,
                "last_name": last_name,
                "patronymic": patronymic,
                "phone": phone,
                "gender": gender,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
                "email_verified": email_verified,
            },
        )

        user.email = email
        user.role = role
        user.first_name = first_name
        user.last_name = last_name
        user.patronymic = patronymic
        user.phone = phone
        user.gender = gender
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.email_verified = email_verified
        if avatar:
            user.avatar = avatar
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    def _seed_offices(self):
        office_specs = [
            {
                "name": "Центральный офис",
                "address": "Иркутск, ул. Ленина, 14",
                "phone": "+7 (3952) 70-10-10",
                "work_hours": "Пн-Пт 08:30-20:00",
                "latitude": 52.286974,
                "longitude": 104.305018,
                "yandex_map_url": "https://yandex.ru/maps/-/CHb26EqP",
                "marker_text": "Центральный офис",
                "parking": "Городская парковка и гостевые места у бизнес-центра",
                "transport": "Остановка \"Сквер Кирова\", 3 минуты пешком",
                "amenities": "Wi-Fi, кофе-поинт, стойка ресепшн, переговорные, принтер",
            },
            {
                "name": "Северный офис",
                "address": "Иркутск, ул. Байкальская, 105А",
                "phone": "+7 (3952) 70-20-20",
                "work_hours": "Пн-Сб 09:00-21:00",
                "latitude": 52.267549,
                "longitude": 104.334704,
                "yandex_map_url": "https://yandex.ru/maps/-/CHb26J3b",
                "marker_text": "Северный офис",
                "parking": "Закрытая парковка на 12 мест",
                "transport": "Остановка \"Байкальская\", 5 минут пешком",
                "amenities": "Wi-Fi, переговорные, lounge-зона, кухня, шкафчики",
            },
            {
                "name": "Технопарк",
                "address": "Иркутск, ул. Академическая, 8",
                "phone": "+7 (3952) 70-30-30",
                "work_hours": "Ежедневно 10:00-22:00",
                "latitude": 52.258631,
                "longitude": 104.260065,
                "yandex_map_url": "https://yandex.ru/maps/-/CHb26Nd7",
                "marker_text": "Технопарк",
                "parking": "Подземный паркинг, первые 2 часа бесплатно",
                "transport": "Трамвай и автобус до остановки \"Академгородок\"",
                "amenities": "Wi-Fi 5G, медиаэкран, кофейня, зона ожидания",
            },
        ]

        offices = {}
        for spec in office_specs:
            office, _ = Office.objects.update_or_create(
                name=spec["name"],
                defaults={
                    "address": spec["address"],
                    "phone": spec["phone"],
                    "work_hours": spec["work_hours"],
                    "latitude": spec["latitude"],
                    "longitude": spec["longitude"],
                    "yandex_map_url": spec["yandex_map_url"],
                    "marker_text": spec["marker_text"],
                    "is_active": True,
                    "parking": spec["parking"],
                    "transport": spec["transport"],
                    "amenities": spec["amenities"],
                },
            )
            offices[spec["name"]] = office
        return offices

    def _seed_rooms(self, offices):
        room_specs = [
            {
                "name": "Фокус",
                "category": "economy",
                "status": "active",
                "office": offices["Центральный офис"],
                "location": "1 этаж, блок A",
                "capacity": 4,
                "price_per_hour": Decimal("500.00"),
                "equipment": "Телевизор\nWi-Fi\nМаркерная доска",
                "amenities": ["Вода", "Кондиционер"],
            },
            {
                "name": "Поток",
                "category": "standard",
                "status": "active",
                "office": offices["Центральный офис"],
                "location": "2 этаж, блок B",
                "capacity": 6,
                "price_per_hour": Decimal("900.00"),
                "equipment": "Проектор\nHDMI\nФлипчарт\nАкустика",
                "amenities": ["Кофе-станция", "Звукоизоляция", "Кондиционер"],
            },
            {
                "name": "Вектор",
                "category": "comfort",
                "status": "active",
                "office": offices["Северный офис"],
                "location": "3 этаж, блок C",
                "capacity": 8,
                "price_per_hour": Decimal("1300.00"),
                "equipment": "Плазменная панель\nКамера для созвонов\nМикрофоны",
                "amenities": ["Кофе", "Панорамные окна", "Быстрый Wi-Fi"],
            },
            {
                "name": "Сфера",
                "category": "vip",
                "status": "active",
                "office": offices["Северный офис"],
                "location": "4 этаж, блок VIP",
                "capacity": 10,
                "price_per_hour": Decimal("1900.00"),
                "equipment": "4K экран\nСистема видеоконференций\nСенсорная панель управления",
                "amenities": ["Сервисный стол", "Премиум мебель", "Шумоизоляция"],
            },
            {
                "name": "Атлас",
                "category": "luxury",
                "status": "active",
                "office": offices["Технопарк"],
                "location": "5 этаж, executive-зона",
                "capacity": 14,
                "price_per_hour": Decimal("2600.00"),
                "equipment": "LED-стена\nСистема записи\nИнтерактивный экран\nАкустика",
                "amenities": ["Секретарь по запросу", "Кофейный сет", "Приватная зона"],
            },
            {
                "name": "Ритм",
                "category": "standard",
                "status": "maintenance",
                "office": offices["Технопарк"],
                "location": "2 этаж, блок D",
                "capacity": 6,
                "price_per_hour": Decimal("850.00"),
                "equipment": "Экран\nWi-Fi",
                "amenities": ["Скоро после ремонта"],
            },
        ]

        rooms = {}
        for spec in room_specs:
            room, _ = Room.objects.update_or_create(
                name=spec["name"],
                defaults={
                    "category": spec["category"],
                    "status": spec["status"],
                    "office": spec["office"],
                    "location": spec["location"],
                    "capacity": spec["capacity"],
                    "price_per_hour": spec["price_per_hour"],
                    "equipment": spec["equipment"],
                    "amenities": spec["amenities"],
                    "is_active": spec["status"] == "active",
                },
            )
            rooms[spec["name"]] = room
        return rooms

    def _seed_faq(self):
        faq_specs = [
            {
                "question": "Как быстро подтверждается бронь?",
                "answer": "Обычно менеджер подтверждает заявку в течение 10-30 минут в рабочее время.",
                "category": "booking",
                "order": 1,
            },
            {
                "question": "Можно ли продлить бронирование?",
                "answer": "Да, если после вашей встречи комната свободна. Лучше заранее продлить время через менеджера.",
                "category": "booking",
                "order": 2,
            },
            {
                "question": "Что входит в стоимость комнаты?",
                "answer": "В стоимость входят доступ к комнате, базовое оборудование, Wi-Fi и общие удобства офиса.",
                "category": "payment",
                "order": 3,
            },
            {
                "question": "Можно ли подключиться по видеосвязи?",
                "answer": "Да, в большинстве комнат есть экран и оборудование для онлайн-встреч.",
                "category": "technical",
                "order": 4,
            },
            {
                "question": "Как отменить бронь?",
                "answer": "Отмену можно сделать в истории бронирований или через менеджера, если бронь уже подтверждена.",
                "category": "general",
                "order": 5,
            },
            {
                "question": "Есть ли парковка у офисов?",
                "answer": "Да, информация о парковке указана на странице офисов у каждого филиала.",
                "category": "general",
                "order": 6,
            },
        ]

        for spec in faq_specs:
            FAQ.objects.update_or_create(
                question=spec["question"],
                defaults={
                    "answer": spec["answer"],
                    "category": spec["category"],
                    "order": spec["order"],
                    "is_active": True,
                },
            )

    def _seed_faq_categories(self):
        category_specs = [
            {"name": "Общее", "slug": "general", "order": 1},
            {"name": "Бронирование", "slug": "booking", "order": 2},
            {"name": "Оплата", "slug": "payment", "order": 3},
            {"name": "Технические вопросы", "slug": "technical", "order": 4},
        ]

        for spec in category_specs:
            FAQCategory.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "name": spec["name"],
                    "order": spec["order"],
                    "is_active": True,
                },
            )

    def _seed_info_sections(self):
        section_specs = [
            {
                "name": "Общая информация",
                "slug": "general",
                "order": 1,
                "description": "Краткие пояснения о работе системы и офисов.",
            },
            {
                "name": "Правила бронирования",
                "slug": "rules",
                "order": 2,
                "description": "Что можно и что нельзя делать при бронировании комнат.",
            },
            {
                "name": "Инструкции",
                "slug": "instructions",
                "order": 3,
                "description": "Пошаговый сценарий бронирования и действий на сайте.",
            },
            {
                "name": "Контакты поддержки",
                "slug": "contacts",
                "order": 4,
                "description": "Как связаться с поддержкой и в какие часы она работает.",
            },
        ]

        for spec in section_specs:
            InfoSection.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "name": spec["name"],
                    "order": spec["order"],
                    "description": spec["description"],
                    "is_active": True,
                },
            )

    def _seed_bookings(self, users, rooms):
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        booking_specs = [
            {
                "user": users["demo_anna"],
                "room": rooms["Поток"],
                "start_time": now - timedelta(days=7, hours=2),
                "end_time": now - timedelta(days=7),
                "status": "completed",
                "participants_count": 4,
                "custom_price": Decimal("1800.00"),
                "booking_full_name": "Анна Лебедева",
                "booking_email": "anna_demo@example.com",
                "booking_phone": "+7 (950) 300-30-30",
                "manager_comment": "Клиент просил HDMI-кабель и воду.",
            },
            {
                "user": users["demo_ivan"],
                "room": rooms["Вектор"],
                "start_time": now + timedelta(days=1, hours=2),
                "end_time": now + timedelta(days=1, hours=5),
                "status": "pending",
                "participants_count": 6,
                "custom_price": None,
                "booking_full_name": "Иван Мельников",
                "booking_email": "ivan_demo@example.com",
                "booking_phone": "+7 (950) 400-40-40",
                "manager_comment": "Нужна подготовка комнаты к презентации.",
            },
            {
                "user": users["demo_olga"],
                "room": rooms["Сфера"],
                "start_time": now + timedelta(days=2, hours=1),
                "end_time": now + timedelta(days=2, hours=3),
                "status": "confirmed",
                "participants_count": 8,
                "custom_price": Decimal("3800.00"),
                "booking_full_name": "Ольга Соколова",
                "booking_email": "olga_demo@example.com",
                "booking_phone": "+7 (950) 500-50-50",
                "manager_comment": "Подтверждено менеджером, подготовить кофе-брейк.",
            },
            {
                "user": users["demo_anna"],
                "room": rooms["Фокус"],
                "start_time": now - timedelta(days=2, hours=1),
                "end_time": now - timedelta(days=2),
                "status": "cancelled",
                "participants_count": 2,
                "custom_price": None,
                "booking_full_name": "Анна Лебедева",
                "booking_email": "anna_demo@example.com",
                "booking_phone": "+7 (950) 300-30-30",
                "manager_comment": "Клиент отменил бронь за день до встречи.",
            },
            {
                "user": users["demo_ivan"],
                "room": rooms["Атлас"],
                "start_time": now + timedelta(days=5, hours=4),
                "end_time": now + timedelta(days=5, hours=7),
                "status": "confirmed",
                "participants_count": 12,
                "custom_price": Decimal("7800.00"),
                "booking_full_name": "Иван Мельников",
                "booking_email": "ivan_demo@example.com",
                "booking_phone": "+7 (950) 400-40-40",
                "manager_comment": "Корпоративная стратегическая сессия.",
            },
        ]

        for spec in booking_specs:
            Booking.objects.update_or_create(
                user=spec["user"],
                room=spec["room"],
                booking_email=spec["booking_email"],
                defaults={
                    "start_time": spec["start_time"],
                    "end_time": spec["end_time"],
                    "status": spec["status"],
                    "participants_count": spec["participants_count"],
                    "custom_price": spec["custom_price"],
                    "booking_full_name": spec["booking_full_name"],
                    "booking_phone": spec["booking_phone"],
                    "manager_comment": spec["manager_comment"],
                },
            )

    def _seed_reviews(self, users, rooms):
        review_specs = [
            {
                "user": users["demo_anna"],
                "room": rooms["Поток"],
                "rating": 5,
                "text": "Удобная комната для встреч, всё было подготовлено вовремя и техника работала без проблем.",
                "status": "approved",
            },
            {
                "user": users["demo_ivan"],
                "room": rooms["Вектор"],
                "rating": 4,
                "text": "Хорошая комната для созвонов, но хотелось бы чуть ярче освещение у доски.",
                "status": "approved",
            },
            {
                "user": users["demo_olga"],
                "room": rooms["Сфера"],
                "rating": 5,
                "text": "Очень приятная атмосфера, комфортные кресла и быстрый интернет для онлайн-переговоров.",
                "status": "approved",
            },
            {
                "user": users["demo_anna"],
                "room": rooms["Фокус"],
                "rating": 4,
                "text": "Небольшая, но аккуратная переговорная. Для коротких встреч вполне подходит.",
                "status": "pending",
            },
        ]

        reviews = {}
        for spec in review_specs:
            review, _ = Review.objects.update_or_create(
                user=spec["user"],
                room=spec["room"],
                defaults={
                    "rating": spec["rating"],
                    "text": spec["text"],
                    "status": spec["status"],
                },
            )
            reviews[(spec["user"].username, spec["room"].name)] = review

        ReviewReply.objects.get_or_create(
            review=reviews[("demo_ivan", "Вектор")],
            user=users["manager_demo"],
            text="Спасибо за отзыв. Подсветку у доски уже включили в план улучшений на этой неделе.",
        )

    def _seed_tickets(self, users):
        now = timezone.now()
        ticket_specs = [
            {
                "user": users["demo_anna"],
                "subject": "Не пришло письмо о подтверждении брони",
                "message": "Создала бронь на завтра, но письмо с подтверждением пока не пришло. Проверьте, пожалуйста.",
                "status": "open",
                "last_activity": now - timedelta(hours=3),
            },
            {
                "user": users["demo_ivan"],
                "subject": "Нужен HDMI-кабель в комнате Вектор",
                "message": "На встречу нужен дополнительный HDMI-кабель и переходник для ноутбука.",
                "status": "in_progress",
                "last_activity": now - timedelta(hours=1),
            },
            {
                "user": users["demo_olga"],
                "subject": "Как изменить время подтверждённой брони?",
                "message": "Можно ли сдвинуть встречу на час позже без полной отмены брони?",
                "status": "closed",
                "last_activity": now - timedelta(days=2),
            },
        ]

        tickets = {}
        for spec in ticket_specs:
            ticket, _ = SupportTicket.objects.update_or_create(
                user=spec["user"],
                subject=spec["subject"],
                defaults={
                    "message": spec["message"],
                    "status": spec["status"],
                    "last_activity": spec["last_activity"],
                    "auto_close_date": spec["last_activity"] + timedelta(days=3),
                },
            )
            tickets[spec["subject"]] = ticket

        responses = [
            {
                "ticket": tickets["Нужен HDMI-кабель в комнате Вектор"],
                "user": users["manager_demo"],
                "message": "Кабель добавили в заявку, в комнате всё будет подготовлено заранее.",
            },
            {
                "ticket": tickets["Как изменить время подтверждённой брони?"],
                "user": users["manager_demo"],
                "message": "Да, можно. Мы уже сдвинули бронь на более позднее время и отправили подтверждение.",
            },
            {
                "ticket": tickets["Как изменить время подтверждённой брони?"],
                "user": users["demo_olga"],
                "message": "Спасибо, всё получила, вопрос закрыт.",
            },
        ]

        for spec in responses:
            TicketResponse.objects.get_or_create(
                ticket=spec["ticket"],
                user=spec["user"],
                message=spec["message"],
            )
