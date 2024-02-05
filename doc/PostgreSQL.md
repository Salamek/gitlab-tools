# Guide how to use/migreate to PostgreSQL (Debian and derivates)

## Install PostgreSQL
```bash
sudo apt update
sudo apt install postgresql
```

## Configure PostgreSQL database and user

Log in as postgres user and start psql console

```bash
su postgres
psql
```

Create user

```psql
CREATE USER gitlab_tools WITH PASSWORD <YOUR_PASSWORD>;
```

Create database

```psql
CREATE DATABASE gitlab_tools;
```

Grant privileges

```psql
GRANT ALL PRIVILEGES ON DATABASE gitlab_tools TO gitlab_tools;
```

Grant usage on schema public to gitlab_tools user
```psql
GRANT USAGE ON SCHEMA public TO gitlab_tools;
```

Set owner of gitlab_tools database to gitlab_tools user

```psql
ALTER DATABASE gitlab_tools OWNER TO gitlab_tools;
```

## Set gitlab-tools configuration to use PostgreSQL database

Edit `/etc/gitlab-tools/config.yml`:

```bash
nano /etc/gitlab-tools/config.yml
```

 and replace value of `SQLALCHEMY_DATABASE_URI` to look ~like this:

```yml
SQLALCHEMY_DATABASE_URI: 'postgresql://gitlab_tools:<YOUR_PASSWORD>@127.0.0.1/gitlab_tools'
```
and save your changes using: <kbd>Ctrl</kbd> + <kbd>o</kbd>


## Create empty database schema

```bash
gitlab-tools create_all
```


## Restart services for gitlab-tools to use new configuration

```bash
systemctl restart gitlab-tools
systemctl restart gitlab-tools_celeryworker
systemctl restart gitlab-tools_celerybeat
```

## Migrate data from old database to PostgreSQL

### SqLite

#### Install sqlite3

```bash
apt install sqlite3
```

#### Dump data from database

```bash
sqlite3 gitlab_tools.db .schema > schema.sql
sqlite3 gitlab_tools.db .dump > dump.sql
grep -vx -f schema.sql dump.sql > data.sql
```

#### Insert data into PostgreSQL

```
su postgres
psql gitlab_tools < /path/to/data.sql
```







