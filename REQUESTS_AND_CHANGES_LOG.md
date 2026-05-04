# Requests And Changes Log

Назначение: единый журнал, где фиксируются пользовательские запросы, выполненные действия, созданные или изменённые файлы, а также следующие шаги.

## Правило ведения

Каждая новая задача должна добавляться новой записью в конец файла.

Шаблон записи:

### YYYY-MM-DD HH:MM
- Request: что запросил пользователь.
- Done: что было реально сделано.
- Files: какие файлы были созданы, изменены или проверены.
- Result: итог текущего шага.
- Next: следующий логический шаг.

## Entries

### 2026-04-30 14:29
- Request: проанализировать полностью структуру проекта, разложить план рефакторинга по этапам, проверить схему данных на соответствие 3NF и создать файл истории запросов/изменений.
- Done: проведён анализ структуры Django-проекта; выделены проблемные зоны в архитектуре, маршрутизации, шаблонах, миграциях и модели данных; создан файл `AGENT_HISTORY.md`; создана дорожная карта `REFACTOR_ROADMAP_3NF.md`; проверена локальная `db.sqlite3` и установлено, что она почти пустая и содержит только миграцию `0001_initial`.
- Files: `AGENT_HISTORY.md`, `REFACTOR_ROADMAP_3NF.md`
- Result: подготовлена полная дорожная карта перехода от текущего монолита к модульной структуре и дана оценка текущей схемы БД относительно 3NF.
- Next: при следующем изменении проекта фиксировать здесь уже конкретные кодовые правки, миграции и принятые решения.

### 2026-04-30 14:31
- Request: подтвердить наличие файла дорожной карты и при необходимости создать явный файл с историей запросов и выполненных действий.
- Done: подтверждено наличие файла `REFACTOR_ROADMAP_3NF.md` в корне проекта; создан отдельный явно названный журнал `REQUESTS_AND_CHANGES_LOG.md`.
- Files: `REQUESTS_AND_CHANGES_LOG.md`
- Result: в проекте теперь есть отдельный файл для истории запросов и изменений с прозрачным названием.
- Next: использовать `REQUESTS_AND_CHANGES_LOG.md` как основной рабочий журнал изменений.

### 2026-04-30 14:35
- Request: уточнено, что `sqlite` нужен только для локальной проверки на ноутбуке, а рабочее окружение на серверах использует `MySQL`; пожелания на будущее: переключатель светлой/тёмной темы, обновление дизайна, улучшение кнопок и общего вида, расширение админского управления по отделам/сущностям, упрощение PDF-генерации без внешнего бинарного файла.
- Done: требования зафиксированы как новые архитектурные и UI-ориентиры для последующих этапов работ.
- Files: `REQUESTS_AND_CHANGES_LOG.md`
- Result: подтверждено, что проект нужно развивать с приоритетом на совместимость с `MySQL`, а `SQLite` оставлять как локальную dev-среду; UI и PDF-часть выделены как отдельные направления последующего рефакторинга.
- Next: уточнить, что именно понимается под "отделами", и определить первый практический шаг внедрения: темы, редизайн, админское управление или PDF.

### 2026-04-30 14:40
- Request: перед началом дальнейших работ настроить git и проверить, подключён ли он к проекту.
- Done: установлено, что проект не был инициализирован как git-репозиторий; создан `.gitignore` с исключением локальных и тяжёлых артефактов; инициализирован git-репозиторий на ветке `main`; подтверждены `user.name` и `user.email`; создан первый локальный коммит `Initial project snapshot`; проверено, что рабочее дерево чистое; подтверждено отсутствие подключённого remote.
- Files: `.gitignore`
- Result: проект полностью готов к локальной работе через git; для подключения к GitHub/GitLab теперь нужен только URL удалённого репозитория.
- Next: если пользователь даст URL remote-репозитория, подключить `origin`; если нет, переходить к реализации переключателя темы.

### 2026-04-30 14:45
- Request: подключить существующий удалённый репозиторий `https://github.com/kirieshka2006/django-project.git` к текущему локальному проекту.
- Done: remote `origin` добавлен к локальному репозиторию; выполнена проверка `git remote -v`; предпринята попытка проверить удалённый репозиторий и его ветки через `git ls-remote`.
- Files: `REQUESTS_AND_CHANGES_LOG.md`
- Result: локальный проект успешно связан с `origin`, но доступ к GitHub по HTTPS из текущей среды требует аутентификацию; без неё нельзя подтянуть ветки и настроить push/pull.
- Next: выбрать способ аутентификации для `origin`: SSH-ключ или HTTPS с токеном/credential helper; после этого проверить remote-ветки и при необходимости настроить upstream для `main`.

### 2026-04-30 14:48
- Request: заменить ранее подключённый remote `origin` на новый репозиторий `https://github.com/kirieshka2006/Diplom.git`.
- Done: выполнена замена URL remote `origin` через `git remote set-url origin ...`; подтверждено локально через `git remote -v`, что fetch/push теперь указывают на новый репозиторий.
- Files: `REQUESTS_AND_CHANGES_LOG.md`
- Result: текущий локальный проект теперь привязан к новому GitHub-репозиторию `Diplom`.
- Next: при необходимости проверить аутентификацию и выполнить первый push в новый репозиторий.

### 2026-04-30 14:52
- Request: выполнить первый push в новый репозиторий `Diplom`.
- Done: предприняты две попытки push: первая с временным переходом на SSH и вторая через HTTPS; пользователь уточнил, что локальный SSH-ключ предназначен для серверов, поэтому remote возвращён на HTTPS-URL.
- Files: `REQUESTS_AND_CHANGES_LOG.md`
- Result: push не выполнен, так как `git` в текущей среде не имеет сохранённых HTTPS-учётных данных для GitHub и завершает работу с ошибкой `could not read Username for 'https://github.com'`.
- Next: настроить git-аутентификацию для GitHub в этой среде и повторить `git push -u origin main`.

### 2026-04-30 14:55
- Request: попробовать настроить авторизацию через GitHub CLI `gh`, чтобы выполнить push в GitHub.
- Done: проверено наличие `gh` и состояние авторизации; установлено, что `gh` в текущей среде не установлен.
- Files: `REQUESTS_AND_CHANGES_LOG.md`
- Result: вариант с GitHub CLI недоступен; для push остаётся настраивать обычную HTTPS-аутентификацию git или выполнять первичную авторизацию вручную вне этой сессии.
- Next: получить рабочие GitHub-учётные данные для git в этой среде или выполнить один успешный `git push` вручную в локальном терминале с авторизацией.

### 2026-04-30 15:02
- Request: проверить, удалось ли пользователю вручную выполнить команды для первого push в `origin`.
- Done: проверено локальное состояние ветки `main`, upstream-конфигурация и список веток на `origin`.
- Files: `REQUESTS_AND_CHANGES_LOG.md`
- Result: push не подтвердился: у локальной `main` нет upstream, а на `origin` не обнаружено ни одной удалённой ветки; репозиторий `Diplom` по факту остаётся пустым.
- Next: повторить `git push -u origin main` в обычном пользовательском терминале с корректной GitHub-аутентификацией или вручную создать первую ветку/коммит через GitHub UI и потом синхронизировать репозиторий.

### 2026-04-30 15:08
- Request: разобрать ошибку `403` при `git push -u origin main` после ручной попытки авторизации пользователя в GitHub по HTTPS.
- Done: проанализировано сообщение `Permission to ... denied`; уточнено, что ошибка возникает уже после ввода логина, значит проблема не в remote URL, а в типе или правах GitHub-аутентификации.
- Files: `REQUESTS_AND_CHANGES_LOG.md`
- Result: наиболее вероятная причина — вместо корректного Personal Access Token был использован пароль GitHub, либо сам токен не имеет прав записи в репозиторий `Diplom`.
- Next: создать или проверить GitHub PAT с доступом к репозиторию `Diplom`, затем повторить `git push -u origin main`.

### 2026-04-30 15:12
- Request: подтвердить, что после настройки GitHub-аутентификации push в новый репозиторий действительно прошёл.
- Done: проверены `git status --branch`, `git branch -vv` и наличие `refs/heads/main` в `origin`; подтверждено, что локальная ветка `main` отслеживает `origin/main`, а удалённая ветка существует.
- Files: `REQUESTS_AND_CHANGES_LOG.md`
- Result: git-часть успешно завершена; проект теперь нормально синхронизируется с GitHub-репозиторием `Diplom`.
- Next: перейти к следующему запланированному шагу — реализации переключателя светлой и тёмной темы.

### 2026-04-30 16:18
- Request: переключить локальную разработку на `SQLite`, оставить `MySQL` как будущий боевой вариант и поднять локальный Django-сервер для просмотра сайта в браузере.
- Done: в `bron/settings.py` активирован `SQLite`-блок `DATABASES`, а текущий `MySQL`-конфиг оставлен рядом закомментированным; выполнены `manage.py check` и `manage.py showmigrations`; подтверждено, что миграции для локальной `SQLite` уже применены; запущен `runserver` на `127.0.0.1:8000`; проверено HTTP-ответом, что главная страница отдаётся с кодом `200 OK`.
- Files: `bron/settings.py`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: локальная среда готова для визуальной проверки интерфейса и дальнейшей разработки переключателя темы.
- Next: приступить к внедрению светлой/тёмной темы поверх текущего шаблонного слоя.

### 2026-04-30 16:26
- Request: заполнить локальный сайт demo-данными, чтобы страницы не были пустыми и можно было проверять интерфейс на реалистичном содержимом.
- Done: добавлена идемпотентная management-команда `seed_demo_data`; в локальную `SQLite` загружены demo-пользователи, офисы, комнаты, бронирования, отзывы, ответы на отзывы, тикеты, ответы техподдержки и FAQ; проверено, что главная страница реально отображает созданные комнаты и офисы.
- Files: `meeting_reservation_system/management/commands/seed_demo_data.py`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: локальный сайт больше не пустой; для повторного наполнения достаточно выполнить `./.venv/bin/python manage.py seed_demo_data`.
- Next: использовать заполненную локальную среду для внедрения переключателя светлой/тёмной темы и дальнейшего редизайна.

### 2026-04-30 16:39
- Request: начать реализацию переключателя светлой и тёмной темы с мягкой светлой палитрой и более насыщенной тёмной палитрой без полного перелопачивания шаблонов.
- Done: добавлены общие include-шаблоны `theme_setup.html` и `theme_toggle.html`; тема внедрена во все полноценные HTML-страницы через общие include перед `</head>` и `</body>`; выбор темы сохраняется в `localStorage`; добавлен плавающий переключатель темы; исправлен побочный артефакт в `room_detail_reviews_script.html`; проверено, что главная и логин рендерят переключатель темы и что `manage.py check` проходит без ошибок.
- Files: `meeting_reservation_system/templates/theme_setup.html`, `meeting_reservation_system/templates/theme_toggle.html`, `meeting_reservation_system/templates/home.html`, `meeting_reservation_system/templates/login.html`, `meeting_reservation_system/templates/register.html`, `meeting_reservation_system/templates/recovery.html`, `meeting_reservation_system/templates/profile.html`, `meeting_reservation_system/templates/offices.html`, `meeting_reservation_system/templates/room_detail.html`, `meeting_reservation_system/templates/support.html`, `meeting_reservation_system/templates/admin_panel.html`, `meeting_reservation_system/templates/admin_user_profile.html`, `meeting_reservation_system/templates/manager_panel.html`, `meeting_reservation_system/templates/report_page.html`, `meeting_reservation_system/templates/users_report.html`, `meeting_reservation_system/templates/room_management_main.html`, `meeting_reservation_system/templates/room_management_category.html`, `meeting_reservation_system/templates/booking_history.html`, `meeting_reservation_system/templates/my_reviews.html`, `meeting_reservation_system/templates/review_moderation.html`, `meeting_reservation_system/templates/all_reviews.html`, `meeting_reservation_system/templates/office_management.html`, `meeting_reservation_system/templates/database_backup.html`, `meeting_reservation_system/templates/info.html`, `meeting_reservation_system/templates/manager_booking_history.html`, `meeting_reservation_system/templates/room_detail_reviews_script.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: сайт уже поддерживает тёмную и светлую тему через общий переключатель; это первый безопасный слой темизации поверх текущих шаблонов.
- Next: визуально проверить тему в браузере и после обратной связи доработать контраст, кнопки и элементы, которые ещё остались в старой палитре.

### 2026-04-30 17:46
- Request: сделать второй проход по теме, чтобы светлая палитра выглядела цельнее не только на главной, но и на логине, поддержке, карточках, выпадающих фильтрах и административных экранах.
- Done: усилен общий `theme_setup.html` без массовой ручной правки отдельных страниц; добавлены общие overrides для карточек, выпадающих меню, price/capacity modal, support/office management блоков, user menu, neutral/accent/danger кнопок, ticket/office hover-состояний, FAQ-градиентов и бейджей комнат; отдельным слоем поправлены стрелки dropdown и цветовые акценты светлой темы под зелёно-бело-серо-коричневую палитру; повторно выполнен `manage.py check`; локально подтверждено, что `/` и `/login/` продолжают отдаваться с кодом `200` и содержат theme toggle.
- Files: `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: второй проход завершён через общий theme-layer; светлая тема стала более связной на основных пользовательских и административных сценариях, при этом структура шаблонов не ломалась.
- Next: визуально проверить страницы в браузере и на основе впечатлений решить, нужен ли третий проход уже точечно по отдельным шаблонам и компонентам.

### 2026-04-30 18:03
- Request: создать отдельный короткий документ с ближайшим планом действий перед уходом пользователя.
- Done: добавлен отдельный файл с тремя ближайшими пунктами работ: фон/тема, PDF, возможная смена дизайна.
- Files: `SHORT_ACTION_PLAN.md`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: краткий ориентир на следующие шаги зафиксирован отдельно от подробного журнала.
- Next: продолжить работу с пункта 1, когда пользователь вернется.

### 2026-05-04 13:29
- Request: вернуться к доработке фона и светлой темы, сделать светлую палитру заметнее и ближе к приглушенной зелено-серо-белой гамме.
- Done: обновлена палитра `light` в `theme_setup.html`; усилен фон страницы через комбинированный `theme-body-overlay + theme-body-gradient`; добавлены более явные стили для `header`, `logo`, `admin/user profile` кнопок, `sidebar`, `filters-card`, `room-card`, `room-image-wrapper`, `room-content`, текстовых акцентов и empty-state; повторно выполнен `manage.py check`; локальный `runserver` поднят на `127.0.0.1:8000`; подтверждено, что `/`, `/login/` и `/support/` отдаются с кодом `200` и содержат theme toggle.
- Files: `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: светлая тема стала заметно темнее, мягче и контрастнее; базовый фон и основные элементы главной теперь должны читаться как отдельная светлая схема, а не как слегка осветленная темная тема.
- Next: визуально проверить страницы в браузере и, если потребуется, точечно добить отдельные шаблоны `home`, `login` и `support`.

### 2026-05-04 13:35
- Request: переработать тёмную тему так, чтобы она не выжигала глаза, оставалась читаемой и чтобы элементы не сливались друг с другом.
- Done: обновлена базовая палитра `dark` в `theme_setup.html` в сторону более мягкой navy/graphite схемы; приглушены синие и фиолетовые акценты; переработаны фоновые градиенты и overlay; добавлены отдельные dark-overrides для `header`, `logo`, `admin/user profile` кнопок, `sidebar`, `filters-card`, `room-card`, `room-image-wrapper`, `room-content`, текстовых акцентов, `empty-state`, а также для hover/focus состояний `header-search`, `custom-dropdown` и `price-filter`; повторно выполнен `manage.py check`; подтверждено, что `/`, `/login/` и `/support/` отдаются с кодом `200` и содержат theme toggle.
- Files: `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: тёмная тема стала спокойнее по цвету, поверхности лучше отделены друг от друга, а ключевые интерактивные элементы больше не должны выглядеть кислотно-синими.
- Next: визуально проверить тёмную тему в браузере и при необходимости точечно довести отдельные страницы вроде `home` и `support`.

### 2026-05-04 13:38
- Request: попробовать более красивый градиент для тёмной темы.
- Done: обновлены `--theme-body-gradient` и `--theme-body-overlay` для `dark` в сторону более глубокого layered-gradient фона с мягкими blue/indigo/teal свечениями; слегка подкрашены `gradient-primary`, `gradient-success`, `surface-card-*`, `header` и `logo-icon`, чтобы тёмная тема выглядела богаче, но без кислотных цветов; повторно выполнен `manage.py check`; подтверждено, что `/` и `/login/` отдаются с кодом `200`.
- Files: `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: у тёмной темы появился более выразительный атмосферный фон, который заметен визуально, но не мешает читаемости интерфейса.
- Next: визуально проверить градиент в браузере и решить, оставляем его как основу или ещё подвинуть оттенки.

### 2026-05-04 13:43
- Request: вернуться к светлой теме, добавить ей более зелёный градиент и исправить чёрные блоки в `ticket_detail` при светлой теме.
- Done: усилен зелёный уклон `light` через обновление `gradient-primary`, `gradient-success`, `surface-card-*`, `theme-body-gradient` и `theme-body-overlay`; в `ticket_detail.html` убраны жёстко заданные тёмные фоны и кнопочные градиенты, вместо них использованы `theme` variables (`surface-card-soft`, `bg-input`, `border-color`, `gradient-primary`, `gradient-success`, `accent-*`); повторно выполнен `manage.py check`; подтверждено, что `/` и `/support/` отдаются с кодом `200`.
- Files: `meeting_reservation_system/templates/theme_setup.html`, `meeting_reservation_system/templates/ticket_detail.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: светлая тема стала заметно зеленее по фону, а содержимое `ticket_detail` теперь должно корректно перекрашиваться вместе с темой вместо чёрных внутренних блоков.
- Next: визуально проверить светлую тему на `support` и, если потребуется, точечно дочистить ещё отдельные фрагменты или модалки.

### 2026-05-04 13:49
- Request: сделать sidebar на главной более аккуратным, убрать наезд на карточки комнат при раскрытии и избавиться от визуально резких углов в светлой теме.
- Done: переработана геометрия `sidebar` в `home.html`: вместо `position: fixed` он переведен в `sticky`-элемент внутри layout, убран `margin-left` у `content-area`, уменьшен и смягчен hover-shift, обновлены размеры, отступы и радиусы `sidebar`, `sidebar-content`, `sidebar-item` и `user-section`; добавлено скругление и clipping для overlay-слоя `user-section::after`; в `theme_setup.html` добавлены отдельные overrides для `sidebar-content` и `user-section` в `light` и `dark`, чтобы сам контейнер и профильный блок выглядели цельно и мягко, а не с жёсткими кромками; повторно выполнен `manage.py check`; подтверждено, что главная отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/home.html`, `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: sidebar больше не должен накладываться на комнаты при раскрытии, а визуально стал мягче по форме и приятнее в обеих темах, особенно в светлой.
- Next: визуально проверить sidebar на главной и при необходимости отдельно дополировать анимацию раскрытия или внутренние карточки.

### 2026-05-04 13:56
- Request: убрать неприятный зелено-красный оттенок у кнопок, иконок и ползунков в светлой теме и сделать акцентные элементы визуально чище.
- Done: очищена акцентная система `light` в `theme_setup.html`: `gradient-primary` и `gradient-success` переведены в более чистый зелёный диапазон, `accent-secondary-rgb` сменён с коричневатого на зелёный, обновлён светлый overlay-фон; поправлены светлые градиенты у `logo-icon`, `logo-text`, `user-section`, `theme-toggle__thumb` и hover-состояния аватара; для `price-slider` добавлены light-overrides для thumb и track без старых синих теней; повторно выполнен `manage.py check`; подтверждено, что главная страница отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: в светлой теме кнопки, иконки и ползунки теперь должны выглядеть более чисто и собранно, без грязноватого зелено-коричневого/красноватого оттенка и без синих следов от старых стилей.
- Next: визуально проверить главную и, если потребуется, точечно дочистить оставшиеся отдельные значки или декоративные бейджи.

### 2026-05-04 14:04
- Request: сделать светлые ползунки в фильтрах менее мутными и добиться поведения, при котором при открытии одного filter-panel второй автоматически закрывает первый.
- Done: в `theme_setup.html` переработаны light-overrides для `.price-slider`: thumb стал более чистым и контрастным, убран мутный переход в треке, снижена визуальная грязь в гамме светлой темы; в `home.html` добавлены helper-функции `closeDropdownMenus`, `closePriceModalPanel`, `closeCapacityModalPanel`, `closeAllFilterPanels`, после чего открытие любого dropdown/price modal/capacity modal теперь сначала закрывает остальные панели, а затем открывает текущую; повторно выполнен `manage.py check`; подтверждено, что главная страница отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/theme_setup.html`, `meeting_reservation_system/templates/home.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: в светлой теме ползунки стали чище по цвету, а логика фильтров теперь соответствует single-open поведению: открытие второго фильтра должно закрывать первый.
- Next: визуально проверить фильтры на главной и при необходимости отдельно подправить ещё только light-state ползунков или анимацию раскрытия панелей.

### 2026-05-04 14:22
- Request: откатить последний заход по переработке фильтра на главной, так как после него интерфейс сломался.
- Done: в `home.html` удалены последний визуальный и JS-слой переработки фильтра, возвращены прежние summary/state-блоки и прежняя логика `applyFilters()`/`showFilterResults()`; в `theme_setup.html` удалены добавленные для этого захода active-state overrides; повторно выполнен `manage.py check`; подтверждено, что `/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/home.html`, `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: главная страница вернулась к состоянию до последнего неудачного редизайна фильтра, при этом более ранние правки по теме, sidebar и single-open логике фильтров сохранены.
- Next: визуально проверить главную и уже потом вносить более точечные и безопасные правки в фильтр небольшими шагами.

### 2026-05-04 14:33
- Request: сделать фильтрацию на главной более миниатюрной, убрать подпись под полем поиска и постараться уложить фильтры в одну строку на desktop.
- Done: в `home.html` удалён helper-текст под `Название комнаты`; уменьшены `filters-card`, summary-блоки, `filter-group`, высота инпута поиска, dropdown-кнопок, price/capacity-кнопок и кнопки `Сбросить`; desktop-grid фильтров перестроен в более компактную 7-колоночную раскладку с fallback на 4/2/1 колонку для меньших экранов; для длинных значений в кнопках добавлен `ellipsis`, чтобы элементы не раздували строку; повторно выполнен `manage.py check`; подтверждено, что `/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/home.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: фильтр на главной стал заметно компактнее и на desktop должен выглядеть ближе к одной строке без лишней высоты и без длинной подписи под поиском.
- Next: визуально проверить главную на твоём экране и, если понадобится, ещё точечно уменьшить только ширину поиска или конкретных dropdown-кнопок.

### 2026-05-04 14:39
- Request: в тёмной теме сделать фильтр на главной более читаемым и контрастным, добавить более заметный акцент, вплоть до фиолетового.
- Done: в `theme_setup.html` переработаны dark-overrides для главного фильтра: `filters-card` получил более выраженный indigo/violet gradient и подсвеченную верхнюю линию; summary-блоки, `filter-group`, `filter-input-shell`, dropdown/button-контролы, reset-кнопки и price/capacity modal получили более светлые и отделённые поверхности; hover/active/select состояния усилены фиолетово-синим акцентом; для dropdown-стрелки и selected-state добавлен более яркий violet-tint; повторно выполнен `manage.py check`; подтверждено, что `/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: в тёмной теме фильтр на главной должен заметно лучше читаться по слоям: контейнер, внутренние блоки и активные элементы больше не должны сливаться в одну плоскость.
- Next: визуально проверить тёмную тему на главной и, если потребуется, либо ещё усилить violet-акцент, либо наоборот сделать его чуть мягче.

### 2026-05-04 14:43
- Request: отдельно выделить `Категорию` в тёмной теме ярче общего блока фильтра и дать её кнопке выбора собственный цвет с читаемым текстом.
- Done: в `home.html` блоку `Категория` добавлен отдельный класс `filter-group-category`; в `theme_setup.html` для него добавлены точечные dark-overrides: сам блок стал ярче общего фильтра, `#categoryFilterBtn` получил отдельный violet/blue gradient, усиленные hover/active состояния и более светлый текст, а `#categoryFilterMenu` и его selected/hover items тоже получили свой более контрастный вариант; повторно выполнен `manage.py check`; подтверждено, что `/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/home.html`, `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: в тёмной теме `Категория` теперь должна заметно выделяться относительно остальных фильтров и читаться как отдельная акцентная точка.
- Next: визуально проверить `Категорию` в тёмной теме и при необходимости отдельно подвинуть либо только насыщенность кнопки, либо только оттенок выпадающего меню.

### 2026-05-04 14:47
- Request: распространить такой же акцентный подход в тёмной теме на остальные фильтры, summary, кнопки `Скрыть`/`Сбросить`, а также убрать внутреннюю прямоугольную focus-обводку у поля `Название комнаты` в светлой и тёмной теме.
- Done: в `home.html` summary-элементам добавлены классы `filters-live-summary__item--results` и `filters-live-summary__item--active`, а блокам `Цена`, `Вместимость`, `Офис`, `Статус комнаты` добавлены отдельные классы для адресного dark-styling; в `theme_setup.html` добавлены общие focus-overrides для `filter-input-shell input`, чтобы внутренняя прямоугольная обводка у текстового поля больше не рисовалась поверх shell; в dark-overrides фильтра отдельно усилены `Название комнаты`, `Цена за час`, `Вместимость`, `Офис`, `Статус комнаты`, summary-блоки, `Скрыть` и основная кнопка `Сбросить` через более контрастные gradient/background/border/text состояния; повторно выполнен `manage.py check`; подтверждено, что `/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/home.html`, `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: в тёмной теме почти все ключевые элементы фильтра на главной теперь должны читаться как отдельные акцентные блоки, а поле поиска больше не должно показывать лишнюю внутреннюю прямоугольную обводку ни в `dark`, ни в `light`.
- Next: визуально проверить тёмную тему на главной и, если потребуется, отдельно приглушить или усилить уже только один-два конкретных акцента, не трогая весь фильтр целиком.

### 2026-05-04 14:54
- Request: сделать `Цена за час`, `Вместимость`, `Офис`, `Статус комнаты` и `Название комнаты` в тёмной теме в том же стиле, что и `Категория`, а также убрать пример `Например: Фокус...` из поля поиска.
- Done: в `home.html` плейсхолдер `searchInput` заменён на нейтральный `Введите название`; в `theme_setup.html` добавлен поздний dark-override-блок, который выравнивает `filter-group-search`, `filter-group-category`, `filter-group-price`, `filter-group-capacity`, `filter-group-office`, `filter-group-status` под один и тот же violet/blue стиль, аналогичный `Категории`; туда же вынесены общие unified-стили для `#categoryFilterBtn`, `#priceFilterBtn`, `#capacityFilterBtn`, `#officeFilterBtn`, `#statusFilterBtn`, а также для меню `#categoryFilterMenu`, `#officeFilterMenu`, `#statusFilterMenu`; повторно выполнен `manage.py check`; подтверждено, что `/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/home.html`, `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: в тёмной теме нужные фильтры теперь должны выглядеть как одна цельная акцентная система в стиле `Категории`, а поле поиска больше не содержит пример с `Фокус/Поток/...`.
- Next: визуально проверить главную в тёмной теме и, если потребуется, уже точечно двигать только насыщенность общего violet/blue стиля, а не каждый фильтр по отдельности.

### 2026-05-04 14:58
- Request: поменять плейсхолдер на `Введите название комнаты` и убрать у текста в поле поиска эффект, похожий на квадратную обводку.
- Done: в `home.html` плейсхолдер `searchInput` изменён на `Введите название комнаты`; в `theme_setup.html` для `filter-input-shell input` усилен cleanup focus-state (`text-shadow: none`, `-webkit-text-stroke: 0`, `filter: none`), а у dark-override для текстового поля и его placeholder убраны эффекты, которые могли давать ощущение контурной обводки; повторно выполнен `manage.py check`; подтверждено, что `/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/home.html`, `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: поле `Название комнаты` теперь должно показывать плейсхолдер `Введите название комнаты`, а текст внутри него должен выглядеть чище, без лишнего контурного эффекта.
- Next: визуально проверить поле поиска в обеих темах и, если понадобится, ещё точечно подвинуть только цвет placeholder.

### 2026-05-04 15:01
- Request: убрать стартовый чёрный прямоугольник вокруг текста/плейсхолдера в поле `Название комнаты` в тёмной теме, который пропадает при hover.
- Done: в `theme_setup.html` добавлен более ранний общий override для `filter-input-shell input`, который теперь всегда принудительно держит `background: transparent`, `border: none`, `box-shadow: none`, `outline: none`, `appearance: none`; повторно выполнен `manage.py check`; подтверждено, что `/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: в поле `Название комнаты` не должно оставаться стартового тёмного прямоугольника внутри shell, а внешний красивый контейнер при этом должен сохраниться.
- Next: визуально проверить именно тёмную тему на главной и, если прямоугольник всё ещё останется, уже адресно проверить browser-specific rendering этого input.

### 2026-05-04 15:36
- Request: исправить ситуацию, когда счётчик активных фильтров на главной стартует с `1`, хотя пользователь ничего не выбирал.
- Done: причина найдена в фильтре `Вместимость`: в разметке были `min/max = 2..20`, но значения и JS-дефолты оставались `1..100`; в `home.html` дефолты `Вместимости` приведены к одному диапазону `2..20` в markup, handlers, display/update logic, active-filter count logic и reset-функциях; повторно выполнен `manage.py check`; подтверждено, что `/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/home.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: счётчик `Фильтров` на главной теперь должен стартовать с `0`, потому что `Вместимость` больше не считается активной по умолчанию.
- Next: визуально обновить главную и проверить, что без действий пользователя summary показывает `Фильтров: 0`.

### 2026-05-04 15:41
- Request: перенести `Сбросить` вверх рядом с `Скрыть`, чтобы при раскрытии sidebar фильтр не ломал подписи, и сделать так, чтобы верхняя кнопка `Сбросить` тоже скрывалась вместе с фильтрами.
- Done: в `home.html` нижняя кнопка `Сбросить` удалена из `filters-grid`; в header actions добавлен новый `filters-reset-main-btn` рядом с `filters-toggle-btn`; desktop-grid фильтров ужат с 7 до 6 колонок; для label добавлен `white-space: nowrap`, чтобы `Статус комнаты` не переносился некрасиво; для `filters-reset-main-btn` добавлены base-стили и логика скрытия через `.filters-card.collapsed .filters-reset-main-btn`; в `theme_setup.html` новый верхний `Сбросить` подключён к тем же dark-overrides, что и `Скрыть`; повторно выполнен `manage.py check`; подтверждено, что `/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/home.html`, `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: `Сбросить` теперь находится сверху рядом с `Скрыть`, не занимает отдельную ячейку сетки фильтров и должен исчезать при сворачивании фильтра, а подпись `Статус комнаты` должна выглядеть стабильнее даже при сужении layout.
- Next: визуально проверить главную при hover sidebar и, если потребуется, уже отдельно решить сам вопрос со смещением layout от sidebar без трогания фильтра.

### 2026-05-04 15:45
- Request: сделать верхнюю кнопку `Сбросить` в той же палитре, что и `Скрыть`, а блок `Найдено` визуально выровнять под блок `Фильтров`.
- Done: в `theme_setup.html` dark-theme overrides для `#filtersResetMainBtn` объединены с `#filtersToggleBtn`, поэтому обе верхние кнопки теперь используют один и тот же violet/blue gradient, hover, border и shadow; стили `filters-live-summary__item--results` объединены со стилем `filters-live-summary__item--active`, чтобы `Найдено` и `Фильтров` выглядели как одна серия summary-карточек; повторно выполнен `manage.py check`; подтверждено, что `/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: в тёмной теме `Сбросить` и `Скрыть` должны выглядеть как парные действия, а `Найдено` больше не должно визуально выбиваться относительно `Фильтров`.
- Next: обновить главную через `Ctrl+F5` и, если понадобится, уже точечно подвинуть только насыщенность или контраст этих верхних акцентных блоков.

### 2026-05-04 15:51
- Request: исправить в светлой теме правую колонку `Бронирование` на странице комнаты, где блоки справа оставались почти чёрными.
- Done: в `theme_setup.html` добавлены light-theme overrides для `room_detail.html`: `right-column`, scrollbar, `calendar`, `time-section`, `duration-section`, `calendar-day`, `time-slot`, `duration-btn`, `booking-summary`, `summary-item`, `contact-form`, `form-group input/textarea` и disabled-state submit теперь используют светлую green/gray палитру вместо жёстких тёмных фонов; повторно выполнен `manage.py check`; подтверждено, что `/room/1/` и `/` отдаются с кодом `200`.
- Files: `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: в светлой теме правая колонка `Бронирование` на странице комнаты должна выглядеть в общей светлой палитре, без чёрных подложек и тёмных полей.
- Next: обновить страницу комнаты через `Ctrl+F5` и, если какой-то отдельный внутренний блок справа всё ещё темноват, уже адресно дожать только его.

### 2026-05-04 15:54
- Request: исправить в светлой теме чёрные блоки в секции `Отзывы` / `info-section` на странице комнаты.
- Done: в `theme_setup.html` добавлены light-theme overrides для `info-section`, `#reviews-stats`, `#add-review-form`, `#edit-review-form`, `#review-text`, `#edit-review-text`, динамических карточек отзывов `[id^='review-card-']` и reply-форм `[id^='reply-form-']`; это перекрывает жёсткие тёмные inline/background стили из `room_detail.html` и приводит секцию отзывов к той же светлой green/gray палитре, что и остальная страница; повторно выполнен `manage.py check`; подтверждено, что `/room/1/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: в светлой теме блок `Отзывы` и его внутренние формы/карточки больше не должны оставаться чёрными.
- Next: обновить страницу комнаты через `Ctrl+F5` и, если в отзывах останется ещё один конкретный тёмный элемент, уже адресно дожать только его.

### 2026-05-04 15:59
- Request: на странице `Офисы` выровнять header, который съезжает и стоит не по центру, и исправить режущую глаз кнопку `Открыть в Яндекс.Картах`.
- Done: в `offices.html` page-header переименован из общего `.header` в отдельный `.offices-header`, убраны жёсткие `width` и `margin-left`, добавлен `max-width: 1200px`, центрирование и нормальная flex-раскладка с левым `back-btn`; у `.yandex-btn` убрана красная заливка, теперь кнопка использует `var(--gradient-primary)` и принудительный белый текст/visited-state, чтобы общие theme-стили ссылок не окрашивали её в зелёный; повторно выполнен `manage.py check`; подтверждено, что `/offices/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/offices.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: header страницы `Офисы` должен стоять по центру и не уезжать, а кнопка `Открыть в Яндекс.Картах` должна выглядеть цельно и читабельно в обеих темах.
- Next: обновить `/offices/` через `Ctrl+F5`; если понадобится, отдельно можно потом перевести сам iframe-виджет карты на JS API, если потребуется скрыть внутренний блок `Открыть в Яндекс.Картах`.

### 2026-05-04 16:05
- Request: на странице `Офисы` сделать зелёный градиент на header, вынести `Назад на главную` влево вверх отдельно от header и показать на iframe-карте точную метку дома.
- Done: в `offices.html` добавлен отдельный `.offices-topbar` над header, куда перенесена кнопка `Назад на главную`; `offices-header` переведён на layered green gradient background с мягкими radial-подсветками; в iframe-карту добавлен параметр `pt={{ office.longitude }},{{ office.latitude }},pm2rdm`, чтобы на карте отображалась явная метка офиса; повторно выполнен `manage.py check`; подтверждено, что `/offices/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/offices.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: header страницы `Офисы` должен выглядеть живее за счёт зелёного градиента, кнопка возврата теперь стоит отдельно слева сверху, а на карте офис должен быть отмечен точкой.
- Next: обновить `/offices/` через `Ctrl+F5`; если понадобится, дальше можно уже полировать сами карточки офисов и нижние инфо-блоки.

### 2026-05-04 16:09
- Request: оставить зелёный градиент на header страницы `Офисы` только в светлой теме, а тёмную тему не менять.
- Done: в `offices.html` базовый фон `.offices-header` возвращён к нейтральному `var(--bg-card)`, а зелёный gradient перенесён в отдельный light-theme override в `theme_setup.html` для `html[data-theme='light'] .offices-header`; повторно выполнен `manage.py check`; подтверждено, что `/offices/` отдается с кодом `200`.
- Files: `meeting_reservation_system/templates/offices.html`, `meeting_reservation_system/templates/theme_setup.html`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: зелёный градиент header теперь должен показываться только в светлой теме, а тёмная тема вернулась к более нейтральному фону без этого изменения.
- Next: обновить `/offices/` через `Ctrl+F5` и проверить обе темы; если нужно, дальше можно подровнять только насыщенность светлого gradient без влияния на dark.

### 2026-05-04 16:15
- Request: начать второй пункт плана и убрать зависимость PDF-экспорта от `wkhtmltopdf/pdfkit`, чтобы PDF работал без внешнего бинарника.
- Done: в `views.py` удалён `pdfkit` и вместо него добавлен pure-Python PDF builder на `Pillow` с кириллическим шрифтом, переносом длинного текста, многостраничной таблицей и общим helper `_build_table_pdf`; `users_export_pdf` и `export_pdf` переведены на новый генератор без HTML->PDF; из `requirements.txt` удалён `pdfkit`; попытка поставить `reportlab` локально не удалась из-за ошибки pip-индекса, поэтому выбран вариант без новой зависимости; повторно выполнен `manage.py check`; через Django test client подтверждено, что `/report/export_pdf/` и `/users-report/export_pdf/` отдают `200`, `application/pdf` и байты начинаются с `%PDF-`.
- Files: `meeting_reservation_system/views.py`, `requirements.txt`, `REQUESTS_AND_CHANGES_LOG.md`
- Result: экспорт PDF теперь не требует `wkhtmltopdf` и должен работать на локалке и на сервере без отдельной установки внешнего exe/bin-файла.
- Next: руками скачать оба PDF из интерфейса и проверить визуально содержание таблиц; если понадобится, следующим шагом можно уже точечно полировать внешний вид PDF или переходить к третьему пункту плана.
