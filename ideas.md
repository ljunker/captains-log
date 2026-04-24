# Ideen

## Inhaltsangabe

### data management
- [datenbank versionierung `[ERLEDIGT]`](#datenbank-versionierung)
- [datenbank backup `[ERLEDIGT]`](#datenbank-backup)
- [anhang-storage konsistenz](#anhang-storage-konsistenz)
- [db vacuum und optimize](#db-vacuum-und-optimize)
- [integrity checks](#integrity-checks)
- [soft delete und papierkorb](#soft-delete-und-papierkorb)
- [retention-regeln](#retention-regeln)
- [anhaenge deduplizieren](#anhaenge-deduplizieren)
- [content hashing](#content-hashing)
- [verschlüsselung at rest](#verschluesselung-at-rest)
- [schema health dashboard](#schema-health-dashboard)
- [bulk repair tools](#bulk-repair-tools)
- [import preview](#import-preview)
- [export snapshots](#export-snapshots)
- [anhang-metadaten extraktion](#anhang-metadaten-extraktion)
- [quota und limits](#quota-und-limits)
- [mehrstufige backup-policy](#mehrstufige-backup-policy)

### deployment
- [version von docker hub ziehen `[ERLEDIGT]`](#version-von-docker-hub-ziehen)
- [automatisches git tag mit patch minor major version `[ERLEDIGT]`](#automatisches-git-tag)
- [healthcheck-aware deploy](#healthcheck-aware-deploy)
- [rollback auf letzte funktionierende version](#rollback-auf-letzte-funktionierende-version)
- [deploy preflight checks](#deploy-preflight-checks)
- [staging deployment](#staging-deployment)
- [zero-downtime deployment](#zero-downtime-deployment)
- [release notes aus git tags](#release-notes-aus-git-tags)
- [deploy lock](#deploy-lock)
- [env validation beim deploy](#env-validation-beim-deploy)
- [post-deploy smoke tests](#post-deploy-smoke-tests)
- [backup vor deploy](#backup-vor-deploy)

### usability
- [tags `[ERLEDIGT]`](#tags)
- [volltextsuche `[ERLEDIGT]`](#volltextsuche)
- [export und import](#export-und-import)
- [erinnerungen](#erinnerungen)
- [kalenderansicht `[ERLEDIGT]`](#kalenderansicht)
- [anhänge `[ERLEDIGT]`](#anhaenge)
- [mehrere benutzer](#mehrere-benutzer)
- [statistik und auswertung](#statistik-und-auswertung)
- [pwa und offline modus](#pwa-und-offline-modus)
- [revisionshistorie](#revisionshistorie)
- [anhang-aufraeumen](#anhang-aufraeumen)
- [offline-create-queue](#offline-create-queue)

## data management

<a id="datenbank-versionierung"></a>
### datenbank versionierung ERLEDIGT
- tabelle für die version anlegen
- wenns die tabelle nicht gibt, anlegen mit version 0
- ordner mit migrationsdateien anlegen, die die änderungen an der datenbankstruktur beschreiben, z.b. neue tabellen, spalten, etc.
- den aktuellen stand bei der entwicklung dieses features als 000_initial.sql speichern, damit die initiale datenbankstruktur erstellt werden kann. da die tabelle dann mit version 0 erstellt wird, muss die 000_initial.sql dann nicht ausgeführt werden
- beim start die migrationsdateien lesen und die versionen vergleichen
- wenn die version der datenbank kleiner ist als die version der migrationsdatei, dann die migration ausführen und die version der datenbank hochsetzen
- migrationsdateien sollten in einem ordner liegen und nach version nummer benannt sein, z.B. 000_initial.sql, 001_add_users.sql, etc.
- migrationsdateien sollten auch eine beschreibung enthalten, z.B. 000_initial.sql könnte die initiale datenbankstruktur erstellen, 001_add_users.sql könnte eine tabelle für benutzer erstellen, etc.

<a id="datenbank-backup"></a>
### datenbank backup ERLEDIGT
- regelmäßige backups der datenbank erstellen, z.B. täglich oder wöchentlich
- backups sollten in einem sicheren ort gespeichert werden, z.B. in der cloud oder auf einem externen speicher
- backups sollten verschlüsselt werden, um die sicherheit zu erhöhen
- backups sollten automatisch gelöscht werden, wenn sie älter als eine bestimmte zeit sind, z.B. 30 tage, um speicherplatz zu sparen
- backups sollten regelmäßig getestet werden, um sicherzustellen, dass sie im notfall wiederhergestellt werden können
- alles über cron jobs automatisieren, damit es keine manuelle arbeit erfordert und regelmäßig durchgeführt wird. die cron jobs müssen auf debian 13 laufen

<a id="anhang-storage-konsistenz"></a>
### anhang-storage konsistenz
- es sollte prüfbar sein, ob jeder anhang in der datenbank auch wirklich noch als datei auf dem dateisystem existiert
- umgekehrt sollten auch dateien erkannt werden, die keinen db-eintrag mehr haben
- ideal wäre ein dry-run und ein reparaturmodus für solche abweichungen

<a id="db-vacuum-und-optimize"></a>
### db vacuum und optimize
- sqlite sollte regelmäßig optimiert werden, damit dateileichen und freier speicher sauber aufgeräumt werden
- dafür wären vacuum, analyze und pragma optimize sinnvolle bausteine
- das könnte als manuelles script oder periodischer wartungsjob laufen

<a id="integrity-checks"></a>
### integrity checks
- zusätzlich zu backups wäre ein eigener gesundheitscheck für die datenbank sinnvoll
- dabei könnten pragma integrity_check, foreign key checks und dateisystem-prüfungen für uploads kombiniert werden
- das ergebnis könnte als kleiner report oder cron-mail ausgegeben werden

<a id="soft-delete-und-papierkorb"></a>
### soft delete und papierkorb
- statt einträge sofort endgültig zu löschen, könnte man sie zuerst in einen papierkorb verschieben
- damit wären versehentliche löschungen einfacher rückgängig zu machen
- später könnte ein cleanup-job solche einträge nach einer frist wirklich entfernen

<a id="retention-regeln"></a>
### retention-regeln
- für revisionsdaten, temporäre dateien oder alte artefakte könnten aufbewahrungsregeln definiert werden
- so wächst die instanz nicht unbegrenzt weiter
- die regeln sollten konfigurierbar sein, z.b. nach alter oder gesamtgröße

<a id="anhaenge-deduplizieren"></a>
### anhaenge deduplizieren
- identische dateien könnten per hash erkannt und nur einmal gespeichert werden
- mehrere einträge könnten dann auf denselben blob verweisen
- das spart speicher, vor allem bei mehrfach hochgeladenen bildern oder audios

<a id="content-hashing"></a>
### content hashing
- auch für einträge selbst könnte ein hash nützlich sein, um doppelte imports oder redundante daten zu erkennen
- das wäre besonders hilfreich für export/import und repair-tools
- die hashes könnten zusätzlich für integritätsprüfungen verwendet werden

<a id="verschluesselung-at-rest"></a>
### verschlüsselung at rest
- sensible daten könnten zusätzlich im ruhenden zustand geschützt werden, nicht nur im backup
- technisch könnte das z.b. über sqlite-verschlüsselung oder hostseitige verschlüsselung gelöst werden
- wichtig wäre dabei ein sauberer schlüssel- und restore-prozess

<a id="schema-health-dashboard"></a>
### schema health dashboard
- eine kleine admin-übersicht könnte db-version, eintragsanzahl, anhangszahl, fehlende dateien und den status letzter checks zeigen
- das wäre praktisch, um auf einen blick zu sehen, ob die instanz gesund ist
- langfristig könnte man dort auch backup- und wartungsstatus einblenden

<a id="bulk-repair-tools"></a>
### bulk repair tools
- für wiederkehrende reparaturen wären kleine scripts sinnvoll, z.b. thumbnails neu bauen, tags normalisieren oder kaputte referenzen bereinigen
- das sollte bewusst getrennt von der normalen app-logik laufen
- ideal wären dry-run und klare zusammenfassungen nach dem lauf

<a id="import-preview"></a>
### import preview
- vor einem import wäre eine analyse sinnvoll, die neue, doppelte und konfliktverdächtige daten anzeigt
- dadurch würde man nicht blind alles einspielen
- so ließen sich imports kontrollierter und sicherer durchführen

<a id="export-snapshots"></a>
### export snapshots
- exports könnten mit metadaten und checksummen als richtige snapshots abgelegt werden
- damit ließe sich besser nachvollziehen, wann welcher export entstanden ist
- so etwas wäre auch nützlich als ergänzung zu backups

<a id="anhang-metadaten-extraktion"></a>
### anhang-metadaten extraktion
- für bilder und audio könnten zusätzliche metadaten wie exif, aufnahmedatum, dauer oder abmessungen gespeichert werden
- das wäre später hilfreich für suche, statistik und bessere darstellung
- bei bildern müsste dabei auf datenschutz und optionale bereinigung geachtet werden

<a id="quota-und-limits"></a>
### quota und limits
- es könnte sinnvoll sein, gesamtgrößen oder anzahlgrenzen für anhänge zu überwachen
- so ließe sich vermeiden, dass das system unbemerkt vollläuft
- warnungen oder harte limits wären beides denkbar

<a id="mehrstufige-backup-policy"></a>
### mehrstufige backup-policy
- zusätzlich zu einem einzelnen backup-ziel könnte man lokale, externe und verifizierte backup-stufen trennen
- so wäre klarer, welche sicherung nur lokal liegt und welche wirklich extern abgesichert ist
- das wäre vor allem für produktivere nutzung sinnvoll

## deployment

<a id="version-von-docker-hub-ziehen"></a>
### version von docker hub ziehen ERLEDIGT
- beim start des containers die version von docker hub ziehen, um sicherzustellen, dass immer die neueste version verwendet wird
- die version könnte in einer umgebungsvariable angegeben werden, z.B. DOCKER_IMAGE_VERSION, oder in einer datei, z.B. version.txt
- wenn die version nicht angegeben ist, könnte eine standardversion verwendet werden, z.B. latest
- die version könnte auch automatisch aktualisiert werden, z.B. durch einen cronjob, der regelmäßig die neueste version von docker hub überprüft und die umgebungsvariable oder die datei aktualisiert, wenn eine neue version verfügbar ist
- beim start des containers könnte auch überprüft werden, ob die aktuelle version mit der neuesten version übereinstimmt, und eine warnung ausgegeben werden, wenn dies nicht der fall ist, um die benutzer zu ermutigen, auf die neueste version zu aktualisieren.

<a id="automatisches-git-tag"></a>
### automatisches git tag mit patch minor major version ERLEDIGT
- ich will ein kleines bash script, was mir automatisch ein git tag erstellt
- ich will "./createtag minor" eingeben, und das script soll sich den letzten git tag holen, die version ordetlich hoch setzen (also von v1.0.1 -> "./createtag minor" -> v1.1.0) und dann den neuen tag erstellen
- das script könnte auch die option haben, die version manuell anzugeben, z.B. "./createtag v1.2.0", um einen bestimmten tag zu erstellen

<a id="healthcheck-aware-deploy"></a>
### healthcheck-aware deploy
- nach einem deploy sollte automatisch geprüft werden, ob die app wirklich gesund hochgekommen ist
- dafür könnte `dockerhub-up` auf `/health` warten und bei fehlschlag den deploy als fehler markieren
- optional könnte erst nach erfolgreichem healthcheck die neue version als aktiv gelten

<a id="rollback-auf-letzte-funktionierende-version"></a>
### rollback auf letzte funktionierende version
- wenn ein deploy fehlschlägt, sollte ein schneller rollback auf die zuletzt funktionierende version möglich sein
- dafür könnte die vorherige image-version oder image-id automatisch protokolliert werden
- ideal wäre ein kleines script wie `./dockerhub-up --rollback`

<a id="deploy-preflight-checks"></a>
### deploy preflight checks
- vor dem eigentlichen deploy könnten grundlegende checks laufen, z.b. ob docker erreichbar ist, genug speicherplatz da ist und das volume gemountet ist
- so würden banale fehler früher auffallen
- das könnte auch nginx- und port-kollisionen mitprüfen

<a id="staging-deployment"></a>
### staging deployment
- zusätzlich zur produktiven compose-datei könnte es einen staging-flow geben
- damit ließen sich neue builds auf einem zweiten port oder einer zweiten subdomain testen, bevor sie live gehen
- sinnvoll wäre auch eine getrennte datenbank oder ein frisches staging-volume

<a id="zero-downtime-deployment"></a>
### zero-downtime deployment
- langfristig könnte das deployment so umgebaut werden, dass kurze ausfälle beim update vermieden werden
- dafür bräuchte es vermutlich zwei app-instanzen und einen proxy-switch
- das ist aufwendiger, aber für produktivere nutzung interessant

<a id="release-notes-aus-git-tags"></a>
### release notes aus git tags
- aus commits zwischen zwei tags könnten automatisch kurze release notes erzeugt werden
- das wäre praktisch, um nach einem deploy direkt zu sehen, was sich geändert hat
- diese infos könnten in eine datei, ins terminal oder in eine kleine deploy-historie geschrieben werden

<a id="deploy-lock"></a>
### deploy lock
- es wäre sinnvoll, parallele deploys zu verhindern
- ein lockfile oder ähnlicher mechanismus könnte verhindern, dass zwei deploy-jobs gleichzeitig laufen
- das reduziert race conditions bei pull, up und migrationsschritten

<a id="env-validation-beim-deploy"></a>
### env validation beim deploy
- vor dem start könnten pflicht-umgebungsvariablen und wichtige pfade geprüft werden
- dazu gehören z.b. api-key, uploads-pfad, root-path oder backup-passphrasen-dateien
- so werden falsch konfigurierte deploys früher abgefangen

<a id="post-deploy-smoke-tests"></a>
### post-deploy smoke tests
- nach einem erfolgreichen start könnten kleine smoke tests laufen, z.b. `/health`, startseite, api und vielleicht ein read-only eintragsaufruf
- das wäre eine gute ergänzung zum einfachen healthcheck
- bei fehlschlag könnte direkt gewarnt oder automatisch zurückgerollt werden

<a id="backup-vor-deploy"></a>
### backup vor deploy
- vor einem produktiven deploy könnte automatisch ein datenbank-backup angestoßen werden
- das wäre besonders wichtig, wenn migrations- oder reparaturschritte beteiligt sind
- der deploy könnte abbrechen, wenn das backup nicht erfolgreich erstellt wurde

## usability

<a id="tags"></a>
### tags ERLEDIGT
- einträge sollen eine optionale liste an tags haben, um sie besser kategorisieren und filtern zu können
- tags könnten in einer eigenen tabelle gespeichert werden, um redundanz zu vermeiden und die wartbarkeit zu erhöhen
- tags könnten auch hierarchisch organisiert werden, z.B. könnte es einen tag "programmieren" geben, der untertags wie "python", "javascript", etc. hat
- tags könnten auch mit farben oder icons versehen werden, um sie visuell ansprechender zu machen und die benutzerfreundlichkeit zu erhöhen
- tags könnten auch in der suche berücksichtigt werden, um die relevanz der suchergebnisse zu erhöhen, z.B. könnte ein eintrag mit dem tag "python" höher in den suchergebnissen erscheinen, wenn nach "python" gesucht wird.
- auch so tags wie "privat" oder "arbeit" könnten nützlich sein, um einträge zu kategorisieren und zu filtern

<a id="volltextsuche"></a>
### volltextsuche ERLEDIGT
- einträge sollten per volltextsuche durchsuchbar sein, nicht nur nach tag oder tag
- sqlite fts5 könnte dafür genutzt werden, damit die suche auch bei vielen einträgen schnell bleibt
- die suche sollte sowohl content als auch tags berücksichtigen
- in der ui könnte es oben ein kleines suchfeld geben, das live filtert oder per enter absendet
- suchtreffer könnten die passenden textstellen kurz hervorheben

<a id="export-und-import"></a>
### export und import
- es sollte einen export aller einträge als json geben, damit man die daten jederzeit aus dem system herausbekommt
- zusätzlich wäre ein markdown export sinnvoll, damit man das tagebuch auch außerhalb der app lesen kann
- ein import aus json wäre praktisch, um backups oder alte daten wieder einzuspielen
- beim import sollte es eine option geben, doppelte einträge zu erkennen und nicht blind alles erneut anzulegen

<a id="erinnerungen"></a>
### erinnerungen
- man könnte tägliche oder wöchentliche erinnerungen einbauen, damit regelmäßig neue einträge entstehen
- technisch wäre das zunächst eher ein serverseitiger cronjob oder eine mail-benachrichtigung
- später könnte daraus auch eine web-push-benachrichtigung werden
- erinnerungen sollten zeitlich konfigurierbar sein, z.B. werktags um 18 uhr

<a id="kalenderansicht"></a>
### kalenderansicht ERLEDIGT
- zusätzlich zur tagesansicht wäre eine kalenderansicht sinnvoll, um schnell zu sehen, an welchen tagen schon einträge existieren
- tage mit vielen einträgen könnten farblich stärker hervorgehoben werden
- ein klick auf einen tag sollte direkt in die bestehende tagesansicht springen
- auf mobile müsste die kalenderansicht reduziert und sehr kompakt sein

<a id="anhaenge"></a>
### anhänge - ERLEDIGT
- einträge könnten optionale dateianhänge bekommen, z.B. bilder, pdfs oder kurze sprachmemos
- dateien sollten nicht direkt in sqlite gespeichert werden, sondern in einem eigenen ordner oder objekt-storage liegen
- in der ui könnte pro eintrag ein kleiner anhangsbereich mit upload und vorschau erscheinen
- bei bildern wäre eine automatische verkleinerung oder thumbnail-erzeugung sinnvoll

<a id="mehrere-benutzer"></a>
### mehrere benutzer
- aktuell ist die app eher für eine person gedacht, aber eine mehrbenutzerfähigkeit könnte interessant sein
- dafür bräuchte es benutzerkonten, sessions und eine trennung der daten pro benutzer
- tags, backups und exports müssten dann benutzerbezogen gedacht werden
- langfristig könnte es auch geteilte logbücher oder teams geben

<a id="statistik-und-auswertung"></a>
### statistik und auswertung
- man könnte einfache auswertungen einbauen, z.B. wie viele einträge pro woche oder pro monat entstanden sind
- zusätzlich wäre spannend, welche tags am häufigsten vorkommen
- eine heatmap über alle tage wäre visuell sehr hilfreich
- die auswertung sollte rein lokal funktionieren und keine externen analysedienste brauchen

<a id="pwa-und-offline-modus"></a>
### pwa und offline modus
- die weboberfläche könnte als progressive web app gebaut werden, damit sie sich auf dem handy fast wie eine native app anfühlt
- ein service worker könnte die statischen assets cachen und zuletzt geladene einträge offline verfügbar machen
- neue einträge könnten offline zwischengespeichert und später synchronisiert werden
- gerade für mobile wäre das nützlich, wenn man unterwegs kurz etwas notieren will

<a id="revisionshistorie"></a>
### revisionshistorie
- bei bearbeiteten einträgen könnte man alte versionen speichern, statt nur updated_at zu setzen
- so ließe sich später nachvollziehen, was an einem eintrag geändert wurde
- technisch könnte es dafür eine entry_revisions tabelle geben
- in der ui könnte man pro eintrag eine kleine history-ansicht öffnen

<a id="anhang-aufraeumen"></a>
### anhang-aufraeumen
- ein kleiner wartungsmodus oder admin-job könnte prüfen, ob dateien im upload-ordner keinen db-eintrag mehr haben oder db-einträge auf fehlende dateien zeigen
- das wäre besonders nach deploys, migrations oder manuellen dateioperationen nützlich
- praktisch wären ein dry-run und ein echter cleanup-modus

<a id="offline-create-queue"></a>
### offline-create-queue
- der pwa-modus könnte neue einträge offline lokal zwischenspeichern und später automatisch synchronisieren
- dabei müsste sichtbar sein, welche einträge noch ausstehen und ob konflikte aufgetreten sind
- das wäre der sinnvolle nächste schritt nach dem bisherigen read-only-offline-cache
