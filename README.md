<div align="center">

# Observatorio Económico y Social de Nariño

### Plataforma Territorial de Inteligencia Económica y Simulación de Políticas

*Analítica territorial, econometría espacial y dinámica, aprendizaje automático interpretable y simulación fiscal para los 64 municipios del departamento de Nariño (Colombia), construida exclusivamente con datos oficiales.*

[![Repositorio](https://img.shields.io/badge/GitHub-javi711%2Fobservatorio__Narino-0f172a?logo=github)](https://github.com/javi711/observatorio_Narino)
![Python](https://img.shields.io/badge/Python-3.11%2B-1e3a8a?logo=python&logoColor=white)
![Gradio](https://img.shields.io/badge/Interfaz-Gradio-f59e0b)
![Plotly](https://img.shields.io/badge/Gr%C3%A1ficos-Plotly-0f172a?logo=plotly&logoColor=white)
![PySAL](https://img.shields.io/badge/Espacial-PySAL%20%2F%20esda-10b981)
![Datos](https://img.shields.io/badge/Datos-100%25%20oficiales-10b981)
![Versión](https://img.shields.io/badge/Versi%C3%B3n-2.0-1e3a8a)

**64 municipios · 13 subregiones · 45 indicadores · 9 dimensiones · 2005–2025 · 10 módulos analíticos**

</div>

---

## Tabla de contenidos

1. [Descripción](#descripción)
2. [Características principales](#características-principales)
3. [Módulos analíticos](#módulos-analíticos)
4. [Datos y fuentes oficiales](#datos-y-fuentes-oficiales)
5. [Política de calidad de datos](#política-de-calidad-de-datos)
6. [Instalación y ejecución](#instalación-y-ejecución)
7. [Configuración](#configuración)
8. [Arquitectura del código](#arquitectura-del-código)
9. [Notas metodológicas](#notas-metodológicas)
10. [Limitaciones conocidas](#limitaciones-conocidas)
11. [Estructura del repositorio](#estructura-del-repositorio)
12. [Cómo citar](#cómo-citar)
13. [Créditos](#créditos)
14. [Aviso](#aviso)

---

## Descripción

El **Observatorio Económico y Social de Nariño** es una aplicación web interactiva que integra, en un solo script de Python, el ciclo completo de análisis territorial: diagnóstico descriptivo, análisis espacial, construcción de tipologías e índices sintéticos, modelación econométrica y de aprendizaje automático, pronóstico, simulación de políticas fiscales e interpretabilidad de modelos.

La plataforma está pensada para dos públicos a la vez:

| Lectura | Público | Qué ofrece |
|---|---|---|
| **Ejecutiva** | Tomadores de decisión, gobiernos locales, ciudadanía | Recuadros en lenguaje claro con hallazgos, semáforos y recomendaciones territoriales |
| **Técnica** | Economistas, econometristas, investigadores | Paneles desplegables «Vista técnica / econometrista» con pruebas formales, coeficientes, errores estándar y diagnósticos |

Todas las cifras provienen de entidades oficiales colombianas (DANE, DNP, MinDefensa, Policía Nacional, MinEducación, MinSalud, MinJusticia/UNODC-SIMCI). **La plataforma no contiene datos simulados ni sintéticos.**

---

## Características principales

- **Cartografía oficial.** Polígonos del Marco Geoestadístico Nacional (MGN 2018, DANE) para los 64 municipios, unidos por código DIVIPOLA de 5 dígitos.
- **Datos en vivo con respaldo verificado.** Al iniciar, el sistema consulta en paralelo las APIs SODA de [datos.gov.co](https://www.datos.gov.co). Si un servidor no responde, usa una instantánea oficial verificada que va dentro del script, de modo que la aplicación funciona incluso sin conexión.
- **Trazabilidad total.** Cada serie indica su entidad, su enlace de origen y si se cargó en vivo o desde la instantánea. Una bitácora de auditoría registra rupturas metodológicas, valores atípicos e imputaciones.
- **Panel de control territorial.** Filtros en cascada por subregión, municipio y periodo que aplican a todos los módulos.
- **Doble modo de lectura** (ejecutiva y técnica) en cada pestaña.
- **Robustez.** Cada gráfico se genera de forma aislada: un error en un cálculo no detiene la aplicación. Los cálculos costosos se guardan en caché.
- **Diseño institucional.** Paleta sobria (azul marino `#0f172a` / `#1e3a8a`), tipografía Inter, tarjetas KPI y semáforo de desempeño (`#10b981` mejora · `#f59e0b` alerta · `#ef4444` deterioro).
- **Convención numérica colombiana** (1.234.567,89) en tablas, gráficos y textos.

---

## Módulos analíticos

| # | Pestaña | Propósito | Métodos |
|:-:|---|---|---|
| 1 | 🏛️ **Inicio** | Pulso económico y social del departamento | KPIs con variación anual, PIB real y crecimiento, estructura sectorial del valor agregado, pobreza, Gini, seguridad, inversión en CTeI e Índice Departamental de Competitividad |
| 2 | 📊 **Radiografía** | Comparar municipios y detectar brechas | EDA, rankings, diagramas de caja por subregión, trayectorias, valores atípicos (IQR y puntaje Z), normalidad, Kruskal-Wallis, correlación de Spearman |
| 3 | 🗺️ **Espacial** | Saber si los problemas se concentran geográficamente | Coropleta continua, I de Moran global, C de Geary, LISA (HH, LL, HL, LH, NS a α = 0,05), mapa de significancia local (p < 0,01 / 0,05 / 0,10), diagrama de dispersión de Moran (pendiente = I), evolución anual del I de Moran |
| 4 | ⛏️ **Tipologías** | Agrupar municipios con perfiles similares | K-Means, clúster jerárquico de Ward, DBSCAN, Silhouette, Calinski-Harabasz, método del codo, proyección PCA 2D, mapa de tipologías |
| 5 | 📉 **Índice PCA** | Resumir muchos indicadores en un índice de 0 a 100 | Análisis de componentes principales, gráfico de sedimentación con criterio de Kaiser, cargas factoriales, biplot, KMO y esfericidad de Bartlett, mapa del Índice Sintético de Desarrollo Territorial |
| 6 | 🤖 **Modelos** | Identificar factores asociados a un resultado | MCO con errores robustos (HC3 / clúster), Ridge, Lasso, ElasticNet, SVR, Random Forest; validación cruzada fuera de muestra (KFold / GroupKFold); residuos frente a ajustados, Q-Q, Breusch-Pagan, RESET, VIF, importancia comparada de variables |
| 7 | 📈 **VAR / VECM** | Estudiar cómo se transmiten los choques entre series | ADF, cointegración de Johansen, VAR en diferencias o VECM, impulso-respuesta ortogonalizada con IC 95 %, descomposición de la varianza (FEVD), raíces inversas y círculo unitario, causalidad de Granger |
| 8 | 🧠 **Pronóstico** | Proyectar tendencias a 5 años | ARIMA con selección por AIC, ETS amortiguado, intervalos de predicción al 95 %, MAPE fuera de muestra, Ljung-Box |
| 9 | 🎯 **Simulador** | Comparar escenarios de política fiscal hasta 2030 | Panel de efectos fijos bidireccionales (municipio y año), choques a recaudo propio (predial + ICA), dependencia de transferencias SGP e inversión; simulación Monte Carlo (1.000 réplicas), gráfico de abanico, ley de Okun |
| 10 | 🔎 **XAI** | Explicar un modelo y diagnosticar un municipio | Random Forest, importancia por permutación, dependencia parcial (PDP), explicación local, perfil radial de percentiles, recomendaciones automáticas |

---

## Datos y fuentes oficiales

### Cobertura

- **Territorio:** departamento de Nariño, 64 municipios en 13 subregiones: Centro, Exprovincia de Obando, Sabana, Abades, Occidente, Cordillera, Juanambú, Río Mayo, Guambuyaco, Pie de Monte Costero, Sanquianga, Pacífico Sur y Telembí.
- **Periodo:** 2005–2025 (según la disponibilidad de cada fuente).
- **Indicadores:** 45 (24 municipales y 20 departamentales, más la población), organizados en 9 dimensiones:

| Dimensión | N.º de indicadores |
|---|:-:|
| Desarrollo social y demografía | 13 |
| Gestión y finanzas públicas | 8 |
| Distribución del ingreso y equidad | 5 |
| Mercado de trabajo | 5 |
| Cuentas económicas y valor agregado | 5 |
| Seguridad ciudadana y orden público | 4 |
| Economías ilícitas y vulnerabilidad | 3 |
| Variables monetarias y costo de vida | 1 |
| Ciencia, tecnología e innovación | 1 |

### Fuentes

| Serie | Entidad | Acceso |
|---|---|---|
| Población municipal (proyecciones 2005–2017 y 2018–2042, CNPV 2018) | DANE | [Proyecciones de población](https://www.dane.gov.co/index.php/estadisticas-por-tema/demografia-y-poblacion/proyecciones-de-poblacion) |
| IPM municipal y privaciones, CNPV 2018 | DANE | [Pobreza multidimensional de fuente censal](https://www.dane.gov.co/index.php/estadisticas-por-tema/pobreza-y-condiciones-de-vida/pobreza-y-desigualdad/medida-de-pobreza-multidimensional-de-fuente-censal) |
| Valor agregado municipal 2011–2024p y por grandes actividades | DANE | [Cuentas departamentales](https://www.dane.gov.co/index.php/estadisticas-por-tema/cuentas-nacionales/cuentas-nacionales-departamentales) |
| PIB de Nariño por ramas 2005–2025pr (base 2015) | DANE | [Cuentas departamentales](https://www.dane.gov.co/index.php/estadisticas-por-tema/cuentas-nacionales/cuentas-nacionales-departamentales) |
| Mercado laboral GEIH (TD, TGP, TO), Pasto A.M. 2007–2025 | DANE | [Empleo y desempleo](https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/empleo-y-desempleo) |
| Informalidad laboral, Pasto A.M. 2021–2025 | DANE | [Empleo informal](https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/empleo-informal-y-seguridad-social) |
| IPC nacional (variación anual) | DANE | [IPC](https://www.dane.gov.co/index.php/estadisticas-por-tema/precios-y-costos/indice-de-precios-al-consumidor-ipc) |
| Pobreza monetaria, pobreza extrema y Gini de Nariño 2021–2025 | DANE | [Pobreza monetaria](https://www.dane.gov.co/index.php/estadisticas-por-tema/pobreza-y-condiciones-de-vida/pobreza-monetaria) |
| IPM departamental 2018–2025 (ECV) | DANE | [Pobreza multidimensional](https://www.dane.gov.co/index.php/estadisticas-por-tema/pobreza-y-condiciones-de-vida/pobreza-multidimensional) |
| Homicidios por municipio | MinDefensa / Policía | API SODA [`m8fd-ahd9`](https://www.datos.gov.co/resource/m8fd-ahd9.json) |
| Secuestros por municipio | MinDefensa | API SODA [`d7zw-hpf4`](https://www.datos.gov.co/resource/d7zw-hpf4.json) |
| Violencia intrafamiliar (denuncias) | Policía Nacional | API SODA [`vuyt-mqpw`](https://www.datos.gov.co/resource/vuyt-mqpw.json) |
| Cultivos de coca por municipio 2001–2024 | MinJusticia / UNODC-SIMCI | API SODA [`acs4-3wgp`](https://www.datos.gov.co/resource/acs4-3wgp.json) |
| Cobertura neta y deserción escolar 2011–2024 | MinEducación | API SODA [`nudc-7mev`](https://www.datos.gov.co/resource/nudc-7mev.json) |
| Partos institucionales 2005–2020 | MinSalud | API SODA [`4e4i-ua65`](https://www.datos.gov.co/resource/4e4i-ua65.json) |
| Medición del Desempeño Municipal 2016–2020 | DNP | API SODA [`nkjx-rsq7`](https://www.datos.gov.co/resource/nkjx-rsq7.json) |
| Índice de Desempeño Fiscal municipal 2005–2022 | DNP | [Información fiscal y financiera](https://www.dnp.gov.co/LaEntidad_/subdireccion-general-descentralizacion-desarrollo-territorial/direccion-descentralizacion-fortalecimiento-fiscal/Paginas/informacion-fiscal-y-financiera.aspx) |
| Inversión en proyectos y sector CTeI (MapaInversiones) | DNP | API SODA [`wc86-9j4a`](https://www.datos.gov.co/resource/wc86-9j4a.json) |
| Índice Departamental de Competitividad | Consejo Privado de Competitividad | [IDC](https://compite.com.co/indice-departamental-de-competitividad/) |
| Límites municipales MGN 2018 (64 polígonos) | DANE (MGN) | [GeoJSON](https://raw.githubusercontent.com/caticoa3/colombia_mapa/master/co_2018_MGN_MPIO_POLITICO.geojson) |

> **Fecha de la instantánea oficial embebida:** 27/10/2026.

---

## Política de calidad de datos

1. **Cero datos simulados.** No hay generadores aleatorios de datos. Los únicos procesos aleatorios son inferenciales (permutaciones, bootstrap, Monte Carlo) y usan semilla fija para que los resultados se puedan reproducir.
2. **Carga en cascada.** Primero se consulta la API en vivo y luego se valida: cobertura mínima de municipios y magnitud coherente con la instantánea (la razón entre ambas debe estar entre 0,4 y 2,5). Si pasa la validación, el dato en vivo prevalece y la instantánea completa los vacíos; si no, se usa la instantánea verificada. El estado de cada fuente se muestra en la pestaña *Inicio*.
3. **Imputación técnica documentada.** Solo se rellenan **huecos interiores** de series anuales, con interpolación monótona **PCHIP**. Nunca se extrapola ni se convierten cortes censales en series anuales. Cada dato imputado se marca con **†** en los gráficos y se registra en la bitácora.
4. **Detección de anomalías.** Los saltos anómalos de un solo año, desviados en el mismo sentido respecto a ambos vecinos, se señalan y se tratan en la bitácora de auditoría. Ejemplo: el salto de cobertura escolar de 2014.
5. **Rupturas metodológicas explícitas.** Por ejemplo, la serie de recursos propios del IDF solo se usa desde 2010 por un cambio de metodología.
6. **Precios constantes.** El valor agregado per cápita se deflacta a pesos de 2015 con el deflactor implícito del valor agregado departamental de Nariño (DANE, base 2015).

---

## Instalación y ejecución

### Opción A · Google Colab (recomendada)

Abra un cuaderno nuevo en [Google Colab](https://colab.research.google.com/), pegue estas dos líneas en una celda y ejecútela:

```python
!wget -q -O app.py https://raw.githubusercontent.com/javi711/observatorio_Narino/main/app.py
%run app.py
```

Otra forma de hacerlo es copiar **todo** el contenido de `app.py` en **una sola celda** y ejecutarla.

En ambos casos, el script instala automáticamente las dependencias que falten. Al terminar la carga aparecerá un enlace público `https://….gradio.live` para abrir el observatorio en el navegador. El enlace dura 72 horas mientras la sesión de Colab siga activa.

### Opción B · Ejecución local

Requisitos: **Python 3.11 o superior** y `git`.

```bash
# 1. Clonar el repositorio
git clone https://github.com/javi711/observatorio_Narino.git
cd observatorio_Narino

# 2. Crear y activar un entorno virtual
python -m venv .venv
source .venv/bin/activate          # En Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

> El script también instala por sí mismo cualquier dependencia que falte, así que el paso 3 es opcional pero recomendado.

```bash
# 4. Ejecutar
python app.py
```

La interfaz queda disponible en `http://127.0.0.1:7860` y, por `share=True`, también en un enlace público temporal de Gradio.

### Tiempo de arranque

Normalmente entre 10 y 40 segundos, según la velocidad de respuesta de datos.gov.co (tiempo máximo por consulta: 30 s). Sin conexión, el observatorio arranca con la instantánea embebida.

---

## Configuración

Los bloques editables están al inicio del script.

**`CREDITOS`**: datos institucionales que se muestran en la ficha técnica y el pie de página.

| Clave | Descripción |
|---|---|
| `autores` | Lista de autores |
| `rol` | Rol de los autores |
| `programa` · `facultad` · `universidad` | Afiliación académica |
| `docente` | Docente tutor |
| `seminario` | Curso o seminario |
| `ciudad_anio` | Lugar y año |

**`CONFIG`**: parámetros de funcionamiento.

| Clave | Valor por defecto | Descripción |
|---|---|---|
| `anio_inicio` | `2005` | Primer año del panel |
| `anio_fin` | `2025` | Último año del panel |
| `timeout_api` | `30` | Tiempo máximo (s) por consulta a las APIs |
| `semilla` | `52` | Semilla de los procesos inferenciales aleatorios |
| `usar_api` | `True` | `False` fuerza el uso exclusivo de la instantánea embebida |
| `geojson_url` | URL MGN-DANE | Origen de la cartografía municipal |
| `fecha_instantanea` | `"27/10/2026"` | Fecha de verificación de la instantánea |

---

## Arquitectura del código

El script es **monolítico por diseño** (una sola celda de Colab) y está organizado en secciones numeradas:

| Sección | Contenido |
|---|---|
| — | Instalación automática de dependencias faltantes (Colab o local) |
| 0–1 | Configuración editable e importaciones |
| 2–3 | Sistema de diseño (paleta, CSS institucional, plantilla Plotly) y formatos numéricos colombianos |
| 4–5 | Catálogo territorial (64 municipios, 13 subregiones, DIVIPOLA) y normalización textual |
| 6–7 | Instantánea oficial embebida y metadatos de los 45 indicadores (unidad, sentido normativo, fuente) |
| 8–9 | Trazabilidad de fuentes y consultas en vivo SODA (en paralelo) |
| 10 | Cartografía MGN-DANE y matrices de pesos espaciales |
| 11–12 | Auditoría de calidad, imputación PCHIP y construcción del panel municipio-año |
| 13–14 | Utilidades de acceso a datos, componentes HTML y cartografía temática |
| 15–24 | Lógica de las 10 pestañas analíticas |
| 25 | Interfaz Gradio (compatible con 4.x, 5.x y 6.x) y lanzamiento |

---

## Notas metodológicas

- **Pesos espaciales.** Contigüidad Queen y Rook calculada sobre los polígonos reales del MGN, k vecinos más cercanos y distancia inversa con umbral. Todas las matrices se estandarizan por filas.
- **Inferencia espacial.** I de Moran global y LISA con **999 permutaciones** (PySAL/esda). Los clústeres LISA se clasifican a α = 0,05.
- **Validación de modelos.** El desempeño se reporta **fuera de muestra**: KFold para cortes transversales y GroupKFold por municipio para paneles, lo que evita filtrar información entre años del mismo municipio.
- **Bandas de impulso-respuesta.** En el VAR se usan intervalos analíticos y en el VECM bootstrap de residuos (200 réplicas).
- **Simulador fiscal.** Las elasticidades salen de un panel de efectos fijos bidireccionales con errores agrupados por municipio y palancas rezagadas un año. La incertidumbre se propaga con β ~ N(β̂, V̂) en 1.000 réplicas de Monte Carlo. El desempleo se vincula al crecimiento mediante la ley de Okun estimada sin 2020–2021.
- **Lectura causal.** Las asociaciones econométricas se interpretan como evidencia condicionada a sus supuestos (exogeneidad, especificación), no como causalidad demostrada.

---

## Limitaciones conocidas

| Tema | Limitación | Tratamiento |
|---|---|---|
| IPM municipal | Solo existe para el CNPV 2018 | Se usa como corte transversal único; no se anualiza |
| Mercado laboral | La GEIH publica TD, TGP y TO para Pasto A.M., no para todo el departamento | Se rotula explícitamente como «Pasto A.M.» |
| Precios | No hay una serie de IPC de Pasto comparable para todo el periodo | Se usa el IPC nacional, rotulado como tal |
| Finanzas públicas | El IDF del DNP cubre 2005–2022 y tiene una ruptura en 2010 (recursos propios) | Se recorta la serie y se registra en la bitácora |
| Series anuales cortas | VAR/VECM y pronósticos trabajan con ~19–21 observaciones | Se presentan como resultados indicativos |
| Simulador | Con los datos 2011–2022 varios efectos no son estadísticamente distintos de cero | Se reportan como «no concluyentes», con su intervalo |
| Denuncias de VIF | Una tasa alta puede reflejar más capacidad institucional para denunciar | Se advierte en el diagnóstico automático |

---

## Estructura del repositorio

```
.
├── app.py                   # Aplicación completa (celda única de Colab / script de Python)
├── requirements.txt         # Dependencias de Python
└── README.md                # Este documento
```

---

## Cómo citar

```bibtex
@software{observatorio_narino_2026,
  title   = {Observatorio Económico y Social de Nariño: Plataforma Territorial
             de Inteligencia Económica y Simulación de Políticas},
  author  = {[Apellidos], Francisco and [Nombre del coinvestigador]},
  year    = {2026},
  version = {2.0},
  address = {San Juan de Pasto, Colombia},
  url     = {https://github.com/javi711/observatorio_Narino}
}
```

---

## Créditos

**Autores:** Francisco [Apellidos] · [Nombre del coinvestigador], estudiantes investigadores
**Programa:** Programa de Economía, [Facultad de Ciencias Económicas y Administrativas], [Nombre de la universidad]
**Docente tutor:** [Nombre del docente tutor]
**Seminario:** [Nombre del seminario / curso]
San Juan de Pasto, 2026

Agradecimientos a las entidades que publican los datos abiertos que hacen posible este trabajo: DANE, DNP, Ministerio de Defensa Nacional, Policía Nacional, Ministerio de Educación Nacional, Ministerio de Salud y Protección Social, Ministerio de Justicia y del Derecho, UNODC-SIMCI y Consejo Privado de Competitividad.

---

## Aviso

Este observatorio es una herramienta académica de análisis y apoyo a la decisión. Las proyecciones y simulaciones describen escenarios condicionados a los datos históricos y a los supuestos de cada modelo; **no son predicciones puntuales ni sustituyen la evaluación técnica de las entidades competentes**. Los datos pertenecen a sus respectivas entidades productoras y se usan conforme a sus condiciones de publicación como datos abiertos.

<div align="center">

---

*Observatorio Económico y Social de Nariño · v2.0 · San Juan de Pasto, 2026*

</div>
