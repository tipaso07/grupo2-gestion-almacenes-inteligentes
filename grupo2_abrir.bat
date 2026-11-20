@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m streamlit run grupo2_gestionDeAlmacenesInteligentes.py
) else (
  python -m streamlit run grupo2_gestionDeAlmacenesInteligentes.py
)
pause
