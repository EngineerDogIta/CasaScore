# CasaScore

Una piccola web-app per chi sta cercando la prima casa: registra ogni immobile
visto, gli assegna un punteggio pesato su criteri configurabili, simula la rata
del mutuo e ti permette di confrontare tutto in un unico colpo d'occhio.

Stack: Python 3.11+ · Streamlit · SQLite (stdlib) · Pandas. Nessuna API esterna,
nessuna autenticazione, dati salvati localmente in `casascore.db`.

## Funzionalità

- **Scheda immobile** — anagrafica, dettagli (mq, locali, classe energetica…),
  preview foto da URL, note libere.
- **Valutazione pesata** — slider 1–5 per 6 criteri di default
  (luminosità, interni, zona, trasporti, rumore, potenziale rivendita) con peso
  modificabile per ogni immobile. Punteggio aggiornato in tempo reale.
- **Dashboard comparativa** — vista card o tabella, ordinabile per
  prezzo / mq / €-mq / punteggio, filtro per stato, statistiche aggregate.
- **Calcolatore mutuo** — ammortamento alla francese, sliders per anticipo,
  durata, tasso. Disponibile sia inline su ogni scheda sia come pagina dedicata.
- **Stato avanzamento** — badge cliccabile: 👀 Da visitare · 📅 Visitato ·
  ❤️ Preferito · ❌ Scartato.

## Installazione

```bash
# (consigliato) ambiente virtuale
python3 -m venv .venv
source .venv/bin/activate

# Install
pip install -r requirements.txt
```

## Avvio

```bash
# Run
streamlit run app.py
```

Al primo avvio viene creato automaticamente `casascore.db` nella cartella del
progetto. Cancellalo per ripartire da zero.

## Struttura

```
casascore/
├── app.py               # Entry point Streamlit + tema CSS
├── db.py                # Schema SQLite + CRUD
├── components/
│   ├── scheda.py        # Form nuova / modifica
│   ├── valutazione.py   # Widget di scoring
│   ├── dashboard.py     # Vista comparativa
│   └── mutuo.py         # Calcolatore mutuo
├── casascore.db         # Creato al primo avvio (gitignored)
└── requirements.txt
```
