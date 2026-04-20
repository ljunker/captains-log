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

### datenbank backup ERLEDIGT
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

### tags ERLEDIGT
- einträge sollen eine optionale liste an tags haben, um sie besser kategorisieren und filtern zu können
- tags könnten in einer eigenen tabelle gespeichert werden, um redundanz zu vermeiden und die wartbarkeit zu erhöhen
- tags könnten auch hierarchisch organisiert werden, z.B. könnte es einen tag "programmieren" geben, der untertags wie "python", "javascript", etc. hat
- tags könnten auch mit farben oder icons versehen werden, um sie visuell ansprechender zu machen und die benutzerfreundlichkeit zu erhöhen
- tags könnten auch in der suche berücksichtigt werden, um die relevanz der suchergebnisse zu erhöhen, z.B. könnte ein eintrag mit dem tag "python" höher in den suchergebnissen erscheinen, wenn nach "python" gesucht wird.
- auch so tags wie "privat" oder "arbeit" könnten nützlich sein, um einträge zu kategorisieren und zu filtern

### volltextsuche ERLEDIGT
- einträge sollten per volltextsuche durchsuchbar sein, nicht nur nach tag oder tag
- sqlite fts5 könnte dafür genutzt werden, damit die suche auch bei vielen einträgen schnell bleibt
- die suche sollte sowohl content als auch tags berücksichtigen
- in der ui könnte es oben ein kleines suchfeld geben, das live filtert oder per enter absendet
- suchtreffer könnten die passenden textstellen kurz hervorheben

### export und import
- es sollte einen export aller einträge als json geben, damit man die daten jederzeit aus dem system herausbekommt
- zusätzlich wäre ein markdown export sinnvoll, damit man das tagebuch auch außerhalb der app lesen kann
- ein import aus json wäre praktisch, um backups oder alte daten wieder einzuspielen
- beim import sollte es eine option geben, doppelte einträge zu erkennen und nicht blind alles erneut anzulegen

### erinnerungen
- man könnte tägliche oder wöchentliche erinnerungen einbauen, damit regelmäßig neue einträge entstehen
- technisch wäre das zunächst eher ein serverseitiger cronjob oder eine mail-benachrichtigung
- später könnte daraus auch eine web-push-benachrichtigung werden
- erinnerungen sollten zeitlich konfigurierbar sein, z.B. werktags um 18 uhr

### kalenderansicht
- zusätzlich zur tagesansicht wäre eine kalenderansicht sinnvoll, um schnell zu sehen, an welchen tagen schon einträge existieren
- tage mit vielen einträgen könnten farblich stärker hervorgehoben werden
- ein klick auf einen tag sollte direkt in die bestehende tagesansicht springen
- auf mobile müsste die kalenderansicht reduziert und sehr kompakt sein

### anhänge - ERLEDIGT
- einträge könnten optionale dateianhänge bekommen, z.B. bilder, pdfs oder kurze sprachmemos
- dateien sollten nicht direkt in sqlite gespeichert werden, sondern in einem eigenen ordner oder objekt-storage liegen
- in der ui könnte pro eintrag ein kleiner anhangsbereich mit upload und vorschau erscheinen
- bei bildern wäre eine automatische verkleinerung oder thumbnail-erzeugung sinnvoll

### mehrere benutzer
- aktuell ist die app eher für eine person gedacht, aber eine mehrbenutzerfähigkeit könnte interessant sein
- dafür bräuchte es benutzerkonten, sessions und eine trennung der daten pro benutzer
- tags, backups und exports müssten dann benutzerbezogen gedacht werden
- langfristig könnte es auch geteilte logbücher oder teams geben

### statistik und auswertung
- man könnte einfache auswertungen einbauen, z.B. wie viele einträge pro woche oder pro monat entstanden sind
- zusätzlich wäre spannend, welche tags am häufigsten vorkommen
- eine heatmap über alle tage wäre visuell sehr hilfreich
- die auswertung sollte rein lokal funktionieren und keine externen analysedienste brauchen

### pwa und offline modus
- die weboberfläche könnte als progressive web app gebaut werden, damit sie sich auf dem handy fast wie eine native app anfühlt
- ein service worker könnte die statischen assets cachen und zuletzt geladene einträge offline verfügbar machen
- neue einträge könnten offline zwischengespeichert und später synchronisiert werden
- gerade für mobile wäre das nützlich, wenn man unterwegs kurz etwas notieren will

### revisionshistorie
- bei bearbeiteten einträgen könnte man alte versionen speichern, statt nur updated_at zu setzen
- so ließe sich später nachvollziehen, was an einem eintrag geändert wurde
- technisch könnte es dafür eine entry_revisions tabelle geben
- in der ui könnte man pro eintrag eine kleine history-ansicht öffnen
