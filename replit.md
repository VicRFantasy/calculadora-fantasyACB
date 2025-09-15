# Fantasy ACB Calculator

## Overview

This is a Fantasy ACB (Spanish basketball league) calculator built with Streamlit. The application allows users to select basketball players while managing a budget constraint of 100 million euros. Players and their prices are loaded from an Excel file, and the interface provides a round-by-round player selection system with real-time budget tracking.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit for web-based user interface
- **Session Management**: Uses Streamlit's session state to persist user selections and budget across interactions
- **Layout**: Column-based layout with dropdowns for player selection and buttons for removing selections

### Data Management
- **Data Source**: Excel file (`jugadores.xlsx`) containing player names and prices
- **Data Processing**: Pandas DataFrame for data manipulation and filtering
- **Price Conversion**: Custom function to convert price strings (in euros with various formats) to standardized millions format
- **State Management**: Session state tracks current budget and selected players across 8 rounds

### Business Logic
- **Budget System**: Fixed initial budget of 100 million euros with real-time tracking
- **Player Selection**: Round-based selection system (8 rounds) with ability to remove selections
- **Price Handling**: Robust price conversion handling multiple currency formats (€ symbols, commas, periods)

### Error Handling
- Price conversion errors are caught and displayed to users
- Fallback to 0.0 for invalid price formats

## External Dependencies

### Python Libraries
- **streamlit**: Web application framework for the user interface
- **pandas**: Data manipulation and analysis for handling player data
- **openpyxl**: Excel file reading capability for loading player information

### Data Dependencies
- **jugadores.xlsx**: Excel file containing player database with names and prices
- File must be located in the same directory as the main application file