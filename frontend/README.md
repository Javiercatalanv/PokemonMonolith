# Frontend de Prueba Angular - NewMonolioPokemon

Aplicacion basica desarrollada en Angular para interactuar y probar todos los endpoints del backend FastAPI.

## Caracteristicas

- Indicadores de salud del backend (Liveness y Readiness).
- Selector dinamico de generaciones (1 a 9) con conteo de registros cargados en PostgreSQL.
- Filtrado por tipo elemental (fuego, agua, planta, veneno, etc.).
- Listado paginado de Pokemon con detalle de estadisticas base y calculo de total de stats.
- Calculo del percentil de poder respecto al total de la base de datos.
- Calculadora de efectividad (matchup) contra tipos atacantes.
- Ranking de los 10 mejores Pokemon por puntuacion de poder.

## Requisitos

- Node.js (v18+ o superior)
- Backend FastAPI en ejecucion en `http://localhost:8000`

## Como ejecutar el Frontend

1. Desde el directorio `frontend/`, instala las dependencias (si aun no lo has hecho):
   ```bash
   npm install
   ```

2. Inicia el servidor de desarrollo de Angular:
   ```bash
   npm start
   ```

3. Abre tu navegador web en:
   ```
   http://localhost:4200
   ```
