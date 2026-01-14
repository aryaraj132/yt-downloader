@echo off
REM Test script for YouTube video downloader
REM Runs the download test with the specified video

echo ============================================
echo YouTube Video Downloader - Test
echo ============================================
echo.

REM Check if virtual environment exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found!
    echo Please run: python -m venv venv
    echo.
)

REM Run the test
python test_download.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Test completed successfully!
) else (
    echo.
    echo Test failed! Check the errors above.
)

pause
