<div dir="rtl">

# whyenv

**متغیر رو عوض کردی و هیچی عوض نشد؟** `whyenv NAME` همه‌ی جاهایی که می‌تونن یک متغیر محیطی رو تعریف کنن (shell خودت، `.env.local`، `.env`، `docker-compose.yml`...) به ترتیبی که **فریم‌ورکت** می‌خونه (Vite، Next.js، Create React App، dotenv ساده، Docker Compose) لیست می‌کنه، برنده رو علامت می‌زنه و می‌گه کدوم ویرایشت نادیده گرفته می‌شه؛ حتی فایل startup شل یا ورودی رجیستری ویندوز که احتمالاً مقدار قدیمی رو export کرده.

![python](https://img.shields.io/badge/python-3.9%2B-blue)
![deps](https://img.shields.io/badge/dependencies-none-brightgreen)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

[English](README.md) | فارسی

</div>

```text
$ whyenv API_URL
whyenv 0.1.1 · API_URL · /tmp/tmpgpidaubx/shop-vite

== Vite (mode=development)
effective value: 'http://old.example.test'   <- from: process environment (your shell)
priority, highest first:
  1. process environment (your shell)             'http://old.example.test'    WINS
       probably set at: ~/.bashrc:3   export API_URL=http://old.example.test
       (whyenv can only see files, not the process that exported it)
  2. .env.development.local                       (no such file)
  3. .env.development                             (no such file)
  4. .env.local:1                                 'http://localhost:3000'      shadowed
  5. .env:2                                       'https://prod.example.test'  shadowed

✗ SHADOWED: edits to .env.local, .env are ignored: the shell already exports API_URL
    why:  vite never overrides a variable that already exists in the process environment; different value(s) in: .env.local (line 1), .env (line 2).
    fix:  remove it from this shell (bash/zsh: `unset API_URL`; PowerShell: `Remove-Item Env:API_URL`; cmd: `set API_URL=`) and restart the dev server; or change the shell value instead. Probably set in: ~/.bashrc:3.

· NOTE: API_URL does not start with VITE_
    why:  vite only exposes VITE_* variables to browser code; reading it there gives undefined (server code and config files can read it)
    fix:  rename to VITE_API_URL if the browser needs it. Never put secrets in VITE_* variables: they end up in the public bundle.

1 confirmed shadowed value(s).
```

<div dir="rtl">

(خروجی `whyenv --demo` که آفلاین سه پروژه‌ی خراب در یک پوشه‌ی موقت می‌سازه؛ خروجی کامل در [docs/demo.txt](docs/demo.txt) هست.)

## چرا؟

کار با `.env` ساده به نظر می‌رسه ولی نیست: متغیری که یک بار در `~/.bashrc` (یا در *Environment Variables* ویندوز) export شده، بی‌صدا از `.env.local` در Vite و Next.js و CRA و dotenv برنده می‌شه؛ مقدارهای `NEXT_PUBLIC_*` و `VITE_*` موقع build داخل بسته‌ی نهایی منجمد می‌شن؛ کانتینر داکر همون محیطی رو نگه می‌داره که با اون ساخته شده؛ و `environment:` از `env_file:` قوی‌تره. آدم‌ها (و ایجنت‌های هوش مصنوعی) جواب می‌دن «سرور رو ریستارت کن»، «node_modules رو پاک کن» و دوباره همون فایل رو ویرایش می‌کنن. `whyenv` حدس رو با قانون واقعیِ اولویت روی فایل‌های واقعی خودت عوض می‌کنه.

## نصب

پایتون ۳٫۹ به بالا، بدون وابستگی. روی لینوکس تست شده؛ خواندن رجیستری ویندوز (`winreg`) و راهنمای PowerShell پیاده شده ولی هنوز روی ویندوز تست نشده.

</div>

```sh
pipx install git+https://github.com/mrzroot/whyenv      # هنوز روی PyPI منتشر نشده
uvx --from git+https://github.com/mrzroot/whyenv whyenv --demo
pip install -e .                                         # از یک کلون محلی
```

<div dir="rtl">

## استفاده

</div>

```sh
whyenv API_URL                        # در پوشه‌ی پروژه‌ی فعلی (فریم‌ورک خودکار تشخیص داده می‌شه)
whyenv API_URL -d ../shop             # پوشه‌ی دیگه
whyenv NEXT_PUBLIC_X -f next -m production   # فریم‌ورک و mode / NODE_ENV رو مشخص کن
whyenv DB_PASSWORD                    # اسم‌های شبیه رمز به‌صورت ‹hidden, N chars› نشون داده می‌شن
whyenv DB_PASSWORD --show-values      # فقط وقتی تنهایی
whyenv API_URL --json                 # خروجی ماشینی
whyenv --demo                         # دموی آفلاین
```

<div dir="rtl">

کد خروج: `0` چیزی shadow نشده، `1` یک مقدار تأییدشده shadow شده، `2` متغیر در هیچ‌کدوم از جاهایی که whyenv نگاه می‌کنه تعریف نشده.

## چه کار می‌کنه

- **اولویت هر فریم‌ورک** طبق مستندات خودشون: Vite (`process > .env.[mode].local > .env.[mode] > .env.local > .env` و فقط `VITE_*` به مرورگر می‌رسه)، Next.js / CRA (`process > .env.$NODE_ENV.local > .env.local (در test نه) > .env.$NODE_ENV > .env` و `NEXT_PUBLIC_` / `REACT_APP_` موقع build درج می‌شن)، dotenv ساده (process برنده است مگر override)، Docker Compose (interpolation: shell > `.env`؛ کانتینر: `environment:` > `env_file:` و فایل‌های بعدی برنده‌ان).
- **منشأ مقدار shell رو پیدا می‌کنه** (تا حد امکان): `~/.bashrc`، `~/.profile`، `/etc/profile.d` و `.envrc` پروژه و پوشه‌های بالاتر؛ در ویندوز کلیدهای رجیستری کاربر و ماشین. با عبارت «احتمالاً در ... تنظیم شده» گزارش می‌شه چون whyenv پروسه‌ای رو که واقعاً export کرده نمی‌بینه.
- **سه سطح**: `SHADOWED` (تأییدشده: یک ویرایش نادیده گرفته می‌شه؛ exit 1)، `CHECK` (می‌تونه علت باشه)، `NOTE` (یک تله‌ی اطراف).
- **تله‌های اطراف مقدار**: نبودن پیشوند کلاینت، پوشه‌ی build قدیمی‌تر از فایل `.env`، مقدار خالیِ برنده، متغیر با اسم مشابه، BOM، CRLF، فاصله دور `=`، گسترش `$`، `#` درون‌خطی، کلید تکراری، کوتیشن بسته‌نشده و کانتینری که دوباره ساخته نشده.
- **رمزها مخفی می‌مونن** به‌صورت پیش‌فرض (اسم‌های دارای KEY، SECRET، TOKEN، PASS...).

### به‌عنوان یک گام برای ایجنت‌ها

محتوای [docs/AGENTS.snippet.md](docs/AGENTS.snippet.md) رو در `AGENTS.md` / `CLAUDE.md` / قوانین Cursor بذار تا دستیار به‌جای ویرایش‌های دور‌ودور `.env` از `whyenv` استفاده کنه.

## محدودیت‌ها (لطفاً بخون)

- فقط **فایل‌ها و رجیستری ویندوز** رو می‌بینه، نه پروسه‌های دیگه. IDE، `-e` داکر، CI یا یک shell والد می‌تونن مقداری بذارن که whyenv فقط به‌صورت «با دست، توسط IDE یا پروسه‌ی والد export شده» گزارش می‌کنه.
- محیطِ پروسه‌ی خودش رو می‌خونه؛ از همون shellی اجراش کن که dev server رو ازش بالا میاری.
- خواننده‌ی Compose یک **زیرمجموعه‌ی حداقلی YAML** هست (services، `environment:` به‌صورت map یا list، `env_file:`)؛ anchor، `extends`، profile و `${VAR:-default}` داخل مقدارها حل نمی‌شن. نتیجه‌ی Compose رو «خیلی محتمل» بدون و با `docker compose config` تأیید کن.
- اولویت‌ها طبق مستندات نسخه‌های فریم‌ورک تا اکتبر ۲۰۲۶ هست؛ اگه فریم‌ورک تغییر کنه ممکنه قانونی کهنه بشه. اگه مغایرتی دیدی issue باز کن.
- قوانین Next.js/CRA به `NODE_ENV` بستگی دارن که whyenv از shell نمی‌خونه: `development` فرض می‌کنه مگر با `-m` عوضش کنی.
- پروژه‌ات رو اجرا نمی‌کنه، چیزی به شبکه نمی‌فرسته و هیچ فایلی نمی‌نویسه.

## توسعه

</div>

```sh
pip install -e ".[test]" && pytest     # ۲۵ تست
```

<div dir="rtl">

MIT · ساخته‌ی [Mohammadreza Zare (mrzroot)](https://github.com/mrzroot) · صفحه‌ی معرفی: https://mrzroot.github.io/whyenv/

</div>
