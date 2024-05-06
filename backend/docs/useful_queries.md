# Useful dabase queries

## Remove duplicate articles (sqlite)

```sql
DELETE FROM article WHERE rowid not in (select min(rowid) from article group by url);
```

## Get all read article titles from a user

```sql
select title from article join userarticlelink on article.id = userarticlelink.article_id join user on userarticlelink.user_id = user.id where user.id = 'USERID';
```

## User stats including how many days they have been active

```sql
select id, created_at, last_request, Cast ((
    JulianDay(last_request) - JulianDay(created_at)
) As Integer) from user order by last_request ;
```

## Get all feeds for a user

```sql
select title, url from feed join userfeedlink on feed.id = userfeedlink.feed_id join user on userfeedlink.user_id = user.id where user.id = 'USERID';
```

## Get all read articles for a user

```sql
select title, url from article join userarticlelink on article.id = userarticlelink.article_id join user on userarticlelink.user_id = user.id where user.id = 'USERID';
```
