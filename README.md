## SAP B1 Reorder Streamlit App

Questa applicazione consente di calcolare in maniera automatica i fabbisogni di riordino a partire da un file di vendite esportato da **SAP Business One**. È pensata per aiutare gli acquirenti a determinare quando e quanto ordinare ai fornitori in base a diversi parametri configurabili.

### Funzionalità principali

* **Upload file Excel**: l’app accetta un file `.xlsx` generato da SAP B1. I nomi delle colonne vengono mappati automaticamente. È possibile specificare un intervallo temporale nel nome del file (esempio: `dal 01.01.25 al 19.08.25`).
* **Calcolo della domanda**: la domanda giornaliera viene calcolata come il massimo tra la quantità spedita nel periodo divisa per i giorni del periodo e la media mensile di vendita negli ultimi 6 mesi convertita in domanda giornaliera. In questo modo si evita di sottostimare o sovrastimare i consumi.
* **Parametri configurabili**: l’utente può definire `lead_time` (giorni necessari ai fornitori per consegnare), `coverage` (giorni di copertura desiderata) e `safety` (giorni di scorta di sicurezza). Questi valori sono utilizzati per calcolare il punto di riordino (`reorder_point`) e il livello target (`target_level`).
* **Fabbisogno di riordino**: per ciascun articolo il fabbisogno viene calcolato come `target_level – projected_available`, dove `projected_available` considera la giacenza totale, gli ordini a fornitori in arrivo e l’impegnato su ordini clienti. Il risultato viene arrotondato al multiplo del collo se presente.
* **Esportazione ordini**: l’app esporta due file Excel: uno contenente l’analisi completa con i dettagli dei calcoli e un altro con un foglio per ciascun fornitore in cui sono elencate le righe da ordinare.

### Struttura del progetto

```
sapb1-reorder-streamlit/
├── app/
│   ├── __init__.py
│   ├── parsing.py
│   ├── io_excel.py
│   ├── rules.py
│   ├── reporting.py
│   └── web/
│       └── streamlit_app.py
├── .streamlit/
│   └── config.toml
├── requirements.txt
├── Dockerfile
└── README.md
```

### Avvio dell’app in locale

Assicurati di avere Python 3.9 o superiore installato. Clona il repository e installa le dipendenze:

```bash
pip install -r requirements.txt
```

Poi avvia l’applicazione Streamlit:

```bash
streamlit run app/web/streamlit_app.py
```

Accedi a `http://localhost:8501` per caricare il file Excel e generare gli ordini.

### Esecuzione su Streamlit Cloud

Per pubblicare l’app su Streamlit Cloud:

1. Effettua il fork di questo repository nel tuo account GitHub.
2. Vai su [streamlit.io/cloud](https://streamlit.io/cloud) e collega il tuo account GitHub.
3. Crea una nuova app, selezionando il repository e impostando il file `app/web/streamlit_app.py` come entry point.
4. Lancia l’app: potrai caricare i tuoi file Excel e scaricare gli ordini di acquisto.

### Configurazione aggiuntiva

Puoi creare un file `vendors.csv` per aggiungere informazioni aggiuntive per ciascun fornitore (codice fornitore, quantità minima d’ordine, lead time specifico, valuta). L’app caricherà questo file automaticamente, se presente nella stessa directory del file Excel caricato.

### Licenza

Questo progetto è rilasciato sotto licenza MIT. Consulta il file `LICENSE` se presente.
