# Entwicklungsprozess und KI-Einsatz

TaskWidgets wurde mit KI-Unterstützung (Claude Code) entwickelt. Konzept,
Funktionsumfang und alle fachlichen Entscheidungen stammen von mir; die KI diente
als Werkzeug für Umsetzung, Refactoring und Tests. Diese Seite dokumentiert das
Vorgehen transparent.

## Konzeption und Vorgaben

Ausgangspunkt war ein klar umrissenes Ziel: ein ressourcenschonendes
Erinnerungs-Widget für Windows 10/11, das vollständig lokal arbeitet. Die
Rahmenbedingungen habe ich festgelegt und konsequent eingehalten:

- reines Python 3 mit `tkinter`, keine externen Abhängigkeiten
- deutschsprachige Oberfläche, Datenhaltung ausschließlich lokal in `%APPDATA%`
- definierter Funktionsumfang (u. a. mehrere Uhrzeiten je Aufgabe, flexible
  Wiederholungen, Ruhemodus, eigener Farbwähler mit Pipette, Export/Import)
- Entscheidung für eine modulare Architektur und einen präsentablen Repo-Aufbau

## Architektur

Die ursprünglich monolithische Anwendung habe ich in fachlich getrennte Module
überführen lassen (siehe „Projektaufbau" in der README), ohne das Verhalten zu
verändern. Technische Kernfrage dabei: wie Zustand – konkret die Theme-Farben für
Hell/Dunkel – zur Laufzeit konsistent an alle Module verteilt wird. Gelöst über
einen zentralen Mechanismus in `config`, der neue Werte live an alle registrierten
Module überträgt.

## Qualitätssicherung

Vor dem Refactoring wurde die lauffähige Version gesichert. Die modulare Fassung
musste nachweislich verhaltensgleich sein. Die Tests liefen durchgängig gegen ein
temporäres Datenverzeichnis, damit produktive Nutzerdaten unberührt blieben.

Geprüft wurden u. a. Programmstart, Themenwechsel, Erinnerungen, Abhaken,
Überspringen, Schlummern, Export/Import, Autostart und der Daten-Rundlauf. Am
6. Oktober 2026 bestanden alle 16 automatisierten Tests sowie ein Kaltstart-Test
als eigenständiger Prozess; ergänzend erfolgte eine manuelle Prüfung der
Oberfläche.

## Eingesetzte Werkzeuge und Kompetenzen

Im Verlauf habe ich mit modularer Strukturierung, Zustandsverwaltung,
Git-Versionierung sowie dem Build eigenständiger `.exe`-Dateien mit PyInstaller
gearbeitet – einschließlich des bekannten False-Positive-Verhaltens von
Virenscannern gegenüber PyInstaller-Binaries. Entscheidungen wie onedir gegen
onefile habe ich bewusst abgewogen statt übernommen.

---

Diese Dokumentation beschreibt das Vorgehen und ist kein vollständiges
Gesprächsprotokoll.
