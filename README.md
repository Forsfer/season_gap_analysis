# Ad-hoc analys över hur gapet mellan tv-säsonger har förändrats

Varje steg exekveras manuellt.
1 - 01_fetch_ids.py hämtar IDn från Discover-endpointen i TMDB:s api. Det ger oss ID och namn på serie.
2 - 02_fetch_details.py hämtar med IDn som parameter in mer detaljrik data för varje serie från Details-endpointen.
3 - season_gap_analysis.ipynb användes för att utforska och rensa data samt transformera data till 4 färdiga tabeller redo att analyseras i Power BI.
