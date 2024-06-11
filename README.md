# docker_images_collector

## Скрипт поиска используемых докер-образов

Q: Зачем нужен такой скрипт?

A: В связи с событиями 30.05.2024 образы с hub.docker.com с российских IP адресов скачать нельзя. Однако 03.06.2024 блокировку сняли. Во избежании повторной блокировки было принято решение загрузить docker-образы преджевременно.

### Задачи, которые будет решать данный скрипт:
- итерироваться по файловой системе рекурсивно, от заданного пути
  - [опционально] итерироваться по органицазии github / репозиториям пользователя / и т.д.
- в случае если каталог является репозиторием, то нужно проитерироваться по всем веткам репозитория
- получать названия всех докер образов из Dockerfile / docker-compose.yml / конфиги github actions / и т.д.
- скачивать все найденные образы с учётом тегов (тег latest не допускается)
- загружать скачанные образы на яндекс.диск, с учетом контрольной суммы, чтобы несколько раз не загружать один и тот же образ