# Polyrhythmik-Kompendium & Rhythm-Engine

Dieses Modul bündelt Theorie, Übung und exakte Zeitraster für Polyrhythmik,
Polymetrik und Video-Synchronisation. Es ergänzt die SYNAPSE-Pipeline mit
mathematisch nachvollziehbaren Daten statt unbelegter Aussagen über
Neurotransmitter oder garantierte Publikumsreaktionen.

## Begriffe

- **Polyrhythmik**: Zwei oder mehr Pulsfolgen teilen einen Zeitrahmen, etwa
  drei gleichmäßige Schläge gegen zwei. Beim 3:2 treffen sich die Stimmen am
  Zyklusanfang; ihre Zwischenpulse liegen bei 0, 1/3, 2/3 und 0, 1/2.
- **Polymetrik**: Unterschiedliche Taktlängen laufen parallel. Bei 4/4 gegen
  3/4 ist der gemeinsame Downbeat-Zyklus zwölf Viertelnoten lang: drei 4/4-
  Takte entsprechen vier 3/4-Takten.
- **Taktart**: Zähler und Nenner beschreiben Gruppierung und Notenwert. 6/8,
  7/8, 7/12, 16/12 und 24/16 sind als notierte Metren gültig; sie sind nicht
  automatisch „irrational“. Bei zusammengesetzten Metren hängt die gefühlte
  Beat-Einheit außerdem von der musikalischen Interpretation ab.
- **Frame-Lock**: Ein musikalischer Zeitpunkt kann zwischen Videoframes liegen.
  Die API liefert deshalb exakte rationale Frame-Positionen und weist aus,
  ob ein Ereignis genau auf einem Frame liegt.

## Einstieg und Übungsweg

1. **Isolation**: Klatsche erst jede Stimme einzeln und halte ein konstantes
   Metronomtempo.
2. **Sprechen**: Nutze Silben oder zähle den gemeinsamen kleinsten Rasterpuls.
3. **Integration**: Klatsche eine Stimme und sprich die andere; tausche dann.
4. **Musikalische Anwendung**: Lege eine Stimme auf Kick/Hi-Hat und die andere
   auf eine Melodie oder Ad-lib. Nimm dich auf und prüfe, ob der Grundpuls stabil
   bleibt.

Ein einfaches Zählmodell für 3:2 ist `1-trip-let, 2-trip-let`: die 3er-Stimme
setzt auf `1`, `trip`, `let`; die 2er-Stimme auf `1` und `let` des gemeinsamen
Rasters. Übe langsam und steigere das Tempo erst, wenn beide Linien einzeln
stabil sind.

## Beispiel: 16 Takte und Videoframes

```python
from synapse.rhythm import generate_meter_timeline

rows = generate_meter_timeline(7, 8, bpm=144, fps=30, bars=16)
for row in rows:
    if row["bar_downbeat"]:
        print(row["bar"], row["time_seconds"], row["frame"])
```

Das Raster enthält für 16 Takte 7/8 insgesamt 112 Zählzeiten. Bei 144 Viertel-
noten-BPM dauert ein 7/8-Takt 1.4583 Sekunden und entspricht bei 30 fps 43.75
Frames; Taktgrenzen liegen daher nicht alle exakt auf einem Frame. Der Renderer
muss den Frame-Rundungsfehler kontrolliert verteilen oder auf einen geeigneten
Zeitbasis-/FPS-Modus wechseln.

## API-Beispiele

```python
from synapse.rhythm import (
    lcm_polyrhythm_grid,
    compute_polymeter_cycle,
    resolve_meter,
)

print(lcm_polyrhythm_grid(3, 2))
print(compute_polymeter_cycle((4, 4), (3, 4), bpm=120, fps=30))
print(resolve_meter(7, 8, bpm=144, fps=30))
```

Run the test suite with `pytest tests/test_rhythm.py -q`.

## Warum Polyrhythmen herausfordernd wirken

Die Herausforderung liegt meist weniger in der Rechnung als darin, zwei
regelmäßige Pulsfolgen unabhängig wahrzunehmen und zugleich einen gemeinsamen
Puls beizubehalten.

- **Puls und Akzent**: Das Ohr sucht oft nach einem stabilen Grundpuls und
  gruppiert Ereignisse in wiederkehrende Akzente. Zwei gleichmäßige Folgen
  können unterschiedliche Gruppierungen nahelegen.
- **Motorische Entkopplung**: Beim Klatschen einer Stimme und Sprechen der
  anderen müssen Aufmerksamkeit und Bewegung zwischen zwei Mustern wechseln.
  Anfänger verschmelzen sie häufig zu einer einzigen synkopierten Linie.
- **Akzent-Erwartung**: Wenn die Betonungen nicht auf vertraute Taktgrenzen
  fallen, kann der Downbeat zunächst unklar wirken. Ein hörbarer gemeinsamer
  Rasterpuls hilft bei der Orientierung.
- **Zyklus und Wiederbegegnung**: Die Pulse des 3:2-Musters treffen sich am
  Zyklusanfang wieder. Diese periodische Rückkehr kann Spannung und Auflösung
  erzeugen; wie sie wirkt, ist jedoch musikalisch und individuell verschieden.

Die Metapher „Kopf klopfen, Bauch reiben“ beschreibt die Koordinationsaufgabe
anschaulich, aber das Gehirn wird dabei nicht buchstäblich in autonome Zentren
aufgespalten. Polyrhythmik ist auch nicht automatisch hypnotisch oder süchtig
machend. Sie ist eine musikalische Struktur, deren Wirkung von Tempo,
Klangfarbe, Akzentuierung, Kontext und Hörerfahrung abhängt.

## Schritt-für-Schritt-Übung: 3 gegen 2

Wähle ein langsames Metronomtempo, zum Beispiel 60 BPM. Ein gemeinsamer Zyklus
wird in sechs gleich große Rasterpunkte geteilt:

```text
Rasterpunkt:  1   2   3   4   5   6
3er-Stimme:   X   .   X   .   X   .
2er-Stimme:   X   .   .   X   .   .
Zählhilfe:    1   &   2   &   3   &
```

Die Tabelle stellt beide Stimmen auf denselben Zeitrahmen: Die 3er-Stimme
spielt auf den Rasterpunkten 1, 3 und 5; die 2er-Stimme auf 1 und 4. Die beiden
Stimmen fallen am Anfang zusammen und haben innerhalb des Zyklus keine weitere
gemeinsame Attacke.

Übe in dieser Reihenfolge:

1. Klatsche nur die 2er-Stimme und zähle gleichmäßig `1 & 2 & 3 &`.
2. Klatsche nur die 3er-Stimme.
3. Klatsche die 2er-Stimme und sprich die 3er-Stimme mit Silben wie `TA-ka-di`.
4. Tausche die Aufgaben.
5. Spiele beide Stimmen leise auf zwei Klangfarben, etwa Handfläche und Finger.
6. Nimm dich auf. Prüfe, ob Tempo und Lautstärke gleichmäßig bleiben, statt nur
   zu versuchen, möglichst schnell zu spielen.

Wenn der Puls auseinanderläuft, gehe zum Metronom zurück und verlangsame das
Tempo. Erst nach mehreren stabilen Wiederholungen solltest du steigern.

## Transfer auf andere Verhältnisse

- **4:3**: Teile einen gemeinsamen Zyklus in zwölf kleine Rasterpunkte. Die
  erste Stimme setzt viermal, die zweite dreimal ein.
- **5:4**: Ein längerer gemeinsamer Zyklus mit mehr Zwischenpositionen. Zuerst
  jede Linie separat üben; beim Zusammenspiel eine Stimme sprechen.
- **Polymetrik 4/4 gegen 3/4**: Halte denselben Viertelpuls, aber zähle die
  Taktgruppen unabhängig. Nach drei 4/4-Takten und vier 3/4-Takten treffen die
  Taktanfänge wieder zusammen.

Die „Tee-Methode“ und andere Sprechsilben sind mnemonische Hilfen, keine
verbindlichen Notationssysteme. Nutze Silben, die sich bei deinem Tempo klar
sprechen lassen.

## Musikalische Anwendung

Polyrhythmik kann als Textur statt als Rechenübung eingesetzt werden:

- Eine gleichmäßige Stimme hält den Grundpuls, eine zweite setzt Akzente
  dagegen.
- Kick oder Bass können die Hauptgruppierung tragen, während Hi-Hat, Percussion
  oder Ad-libs eine andere Unterteilung markieren.
- Im Arrangement kann zunächst nur eine Stimme erklingen; die zweite kommt
  später hinzu, damit die rhythmische Spannung nachvollziehbar bleibt.
- Bei Wechseln zwischen 4/4, 6/8 oder 7/8 helfen klare Übergangsakzente und
  ein kurzer gemeinsamer Puls, den neuen Takt hörbar zu machen.

Höre unterschiedliche Traditionen und Stücke respektvoll im musikalischen
Kontext: Polyrhythmik ist in vielen Musikkulturen verwurzelt und nicht bloß ein
Effekt oder eine mathematische Spielerei.

## Audio-visuelle Gestaltung: verantwortungsvolle Defaults

Beat-Sync, Zoom, Farbwechsel und Schnitte sind kreative Werkzeuge, keine
Methode zur Kontrolle von Bewusstsein oder Dopamin. Keine Strobe- oder
Flackerfrequenzen verwenden, die photosensitive Zuschauer gefährden könnten;
bei schnellen Helligkeitswechseln konservative Grenzwerte, Warnhinweise und
eine nicht-flackernde Alternative anbieten. Audio-Mastering muss Pegelspitzen,
Kopfhörer- und Lautsprecherwiedergabe sowie geltende Loudness-Ziele prüfen.

## Weiterführende Übungsquellen

Als Einstieg in praktische Übungen und Erklärungen können die vom Projekt
zusammengetragenen Materialien der Open Music Academy, der Schlagzeugschule
Berlin, startdrumming.de und LANDR dienen. Prüfe bei externen Quellen jeweils
Notation, Terminologie und kulturellen Kontext; die Zusammenfassung hier ist
keine wörtliche Wiedergabe dieser Beiträge.
