# KI-Unterstützung bei TaskWidgets

## Überblick

TaskWidgets habe ich mit KI-Unterstützung entwickelt (Claude Code). Die Idee,
der Funktionsumfang, das Design und alle Entscheidungen stammen von mir. Den
Code habe ich gemeinsam mit der KI erarbeitet; ich habe Ziele vorgegeben,
Vorschläge bewertet, die Umsetzung freigegeben und die Ergebnisse geprüft.

Als Auszubildender zum Fachinformatiker für Anwendungsentwicklung nutze ich das
Projekt, um die Werkzeuge und Abläufe einer modernen Entwicklung kennenzulernen
und zu verstehen – nicht, um Code unbesehen zu übernehmen.

## Was von mir kam

- Idee und Zweck: ein schlankes, lokales Erinnerungs-Widget für Windows 11
- Funktionen: Uhr und nächste Aufgaben, Erinnerungen mit Ton, Wiederholungen,
  mehrere Uhrzeiten pro Aufgabe, Ruhemodus, Verlauf, helles/dunkles Design,
  eigene Farben mit Pipette, Export/Import, Tray-Symbol
- Rahmenbedingungen: reines Python 3 mit `tkinter`, keine externen Pakete,
  deutsche Oberfläche, Daten nur lokal in `%APPDATA%`
- Entscheidungen im Ablauf: Aufteilung des Codes in Module, Aufbau fürs
  GitHub-Profil, Auswahl und Gestaltung der Screenshots

## Ablauf

Zuerst entstand eine funktionierende Einzeldatei. Danach habe ich den Code in
klar getrennte Module aufteilen lassen (siehe „Projektaufbau" in der README),
ohne das Verhalten zu ändern. Vor der Aufteilung habe ich eine Sicherung der
laufenden Version angelegt und darauf bestanden, dass die aufgeteilte Version
nachweislich genauso funktioniert.

Anschließend habe ich das Projekt für GitHub vorbereitet: `.gitignore`, Lizenz,
README mit Screenshots sowie die Git-Historie.

## Prüfung der Änderungen

Die aufgeteilte Version wurde automatisiert getestet (Start ohne Oberfläche,
Themenwechsel hell/dunkel, Erinnerungen, Abhaken, Überspringen, Schlummern,
Export/Import, Autostart, Daten-Rundlauf). Alle Tests liefen gegen ein
temporäres Datenverzeichnis, damit die echten Aufgaben unberührt blieben.

Am 6. Oktober 2026 bestanden alle 16 automatisierten Tests sowie ein separater
Kaltstart-Test (Start als eigener Prozess). Zusätzlich habe ich die App selbst
gestartet und die Oberfläche geprüft.

## Was ich dabei gelernt habe

- Aufteilung eines größeren Programms in Module und sauberes Weitergeben von
  Zustand (hier: die Theme-Farben) zwischen den Modulen
- Grundlagen von Git: Commits, Historie, `.gitignore`
- Erstellen einer eigenständigen `.exe` mit PyInstaller und der Umgang mit
  einem bekannten Fehlalarm von Virenscannern (*False Positive*)
- Aufbau einer aussagekräftigen README mit Screenshots

## Hinweis

Diese Seite beschreibt den Ablauf und ist kein vollständiges Gesprächsprotokoll.
