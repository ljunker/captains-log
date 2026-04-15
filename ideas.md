# Ideen

## data management

### datenbank versionierung
- tabelle für die version anlegen
- wenns die tabelle nicht gibt, anlegen mit version 0
- bei jedem update die version hochsetzen
- beim start die migrationsdateien lesen und die versionen vergleichen
- wenn die version der datenbank kleiner ist als die version der migrationsdatei, dann die migration ausführen und die version der datenbank hochsetzen
- migrationsdateien sollten in einem ordner liegen und nach version nummer benannt sein, z.B. 001_initial.sql, 002_add_users.sql, etc.
- migrationsdateien sollten auch eine beschreibung enthalten, z.B. 001_initial.sql könnte die initiale datenbankstruktur erstellen, 002_add_users.sql könnte eine tabelle für benutzer erstellen, etc.

### datenbank backup
- regelmäßige backups der datenbank erstellen, z.B. täglich oder wöchentlich
- backups sollten in einem sicheren ort gespeichert werden, z.B. in der cloud oder auf einem externen speicher
- backups sollten verschlüsselt werden, um die sicherheit zu erhöhen
- backups sollten automatisch gelöscht werden, wenn sie älter als eine bestimmte zeit sind, z.B. 30 tage, um speicherplatz zu sparen
- backups sollten regelmäßig getestet werden, um sicherzustellen, dass sie im notfall wiederhergestellt werden können