# Useful dabase queries

## Remove duplicate articles (sqlite)
```sql
DELETE FROM article WHERE rowid not in (select min(rowid) from article group by url);
```
