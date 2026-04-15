# Ideen

## data management

### datenbank versionierung ERLEDIGT
- tabelle für die version anlegen
- wenns die tabelle nicht gibt, anlegen mit version 0
- ordner mit migrationsdateien anlegen, die die änderungen an der datenbankstruktur beschreiben, z.b. neue tabellen, spalten, etc.
- den aktuellen stand bei der entwicklung dieses features als 000_initial.sql speichern, damit die initiale datenbankstruktur erstellt werden kann. da die tabelle dann mit version 0 erstellt wird, muss die 000_initial.sql dann nicht ausgeführt werden
- beim start die migrationsdateien lesen und die versionen vergleichen
- wenn die version der datenbank kleiner ist als die version der migrationsdatei, dann die migration ausführen und die version der datenbank hochsetzen
- migrationsdateien sollten in einem ordner liegen und nach version nummer benannt sein, z.B. 000_initial.sql, 001_add_users.sql, etc.
- migrationsdateien sollten auch eine beschreibung enthalten, z.B. 000_initial.sql könnte die initiale datenbankstruktur erstellen, 001_add_users.sql könnte eine tabelle für benutzer erstellen, etc.

### datenbank backup
- regelmäßige backups der datenbank erstellen, z.B. täglich oder wöchentlich
- backups sollten in einem sicheren ort gespeichert werden, z.B. in der cloud oder auf einem externen speicher
- backups sollten verschlüsselt werden, um die sicherheit zu erhöhen
- backups sollten automatisch gelöscht werden, wenn sie älter als eine bestimmte zeit sind, z.B. 30 tage, um speicherplatz zu sparen
- backups sollten regelmäßig getestet werden, um sicherzustellen, dass sie im notfall wiederhergestellt werden können
- alles über cron jobs automatisieren, damit es keine manuelle arbeit erfordert und regelmäßig durchgeführt wird. die cron jobs müssen auf debian 13 laufen

## deployment

### version von docker hub ziehen ERLEDIGT
- beim start des containers die version von docker hub ziehen, um sicherzustellen, dass immer die neueste version verwendet wird
- die version könnte in einer umgebungsvariable angegeben werden, z.B. DOCKER_IMAGE_VERSION, oder in einer datei, z.B. version.txt
- wenn die version nicht angegeben ist, könnte eine standardversion verwendet werden, z.B. latest
- die version könnte auch automatisch aktualisiert werden, z.B. durch einen cronjob, der regelmäßig die neueste version von docker hub überprüft und die umgebungsvariable oder die datei aktualisiert, wenn eine neue version verfügbar ist
- beim start des containers könnte auch überprüft werden, ob die aktuelle version mit der neuesten version übereinstimmt, und eine warnung ausgegeben werden, wenn dies nicht der fall ist, um die benutzer zu ermutigen, auf die neueste version zu aktualisieren.

### automatisches git tag mit patch minor major version ERLEDIGT
- ich will ein kleines bash script, was mir automatisch ein git tag erstellt
- ich will "./createtag minor" eingeben, und das script soll sich den letzten git tag holen, die version ordetlich hoch setzen (also von v1.0.1 -> "./createtag minor" -> v1.1.0) und dann den neuen tag erstellen
- das script könnte auch die option haben, die version manuell anzugeben, z.B. "./createtag v1.2.0", um einen bestimmten tag zu erstellen

## usability

### tags
- einträge sollen eine optionale liste an tags haben, um sie besser kategorisieren und filtern zu können
- tags könnten in einer eigenen tabelle gespeichert werden, um redundanz zu vermeiden und die wartbarkeit zu erhöhen
- tags könnten auch hierarchisch organisiert werden, z.B. könnte es einen tag "programmieren" geben, der untertags wie "python", "javascript", etc. hat
- tags könnten auch mit farben oder icons versehen werden, um sie visuell ansprechender zu machen und die benutzerfreundlichkeit zu erhöhen
- tags könnten auch in der suche berücksichtigt werden, um die relevanz der suchergebnisse zu erhöhen, z.B. könnte ein eintrag mit dem tag "python" höher in den suchergebnissen erscheinen, wenn nach "python" gesucht wird.
- auch so tags wie "privat" oder "arbeit" könnten nützlich sein, um einträge zu kategorisieren und zu filtern
