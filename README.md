# Projet Dataviz : le massif landais devient-il méditerranéen ?

Module **Concevoir une dataviz**, M2 IA/Data, Ynov Campus Aix (octobre 2026).

Equipe : Ziyad Berjane, Mehdi Bousetta, Walid Makboul

Tableau de bord interactif comparant le risque d'incendie de forêt du massif des Landes de Gascogne
(Gironde + Landes) à celui des Alpes-Maritimes : climat, incendies 2006-2025, prévention et moyens de lutte.

| Dossier | Contenu |
|---|---|
| [`projet/`](projet/) | Le projet : données, préparation, dashboard Dash + Plotly et dashboard Streamlit + Altair. Voir son [README](projet/README.md). |
| [`cours/`](cours/) | Supports du cours (diapositives, notebooks, TP), sans lien direct avec le code du projet. |

## Lancer un dashboard

Sous Windows, double-clic sur :
- `lancer_ecran.bat` : rapport façon Power BI en 5 pages (http://127.0.0.1:8052) ;
- `lancer_dash.bat` : version longue Dash (http://127.0.0.1:8050) ;
- `lancer_altair.bat` : version Streamlit + Altair (http://localhost:8501).

Sinon, depuis le dossier `projet/` :

```bash
pip install -r requirements.txt
python app_dash/ecran.py
python app_dash/app.py
streamlit run app_altair/app.py
```
