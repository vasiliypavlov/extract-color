# Color Palette Extractor

[🇷🇺 Читать на русском](#русский-вариант) | [🇺🇸 Read in English](#english-version)

---

## Русский вариант

**Color Palette Extractor** — CLI-инструмент для рекурсивного извлечения доминирующих цветов из изображений. Поддерживает квантование (`fastoctree`, `mediancut`, `kmeans`), сортировку по оттенкам, создание PNG-плиток и экспорт в HEX, webcolors, а также расширенную палитру **XKCD (949 цветов)**, оптимизированную для текстовых кодировщиков (T5, BERT). Использует пространство CIELAB и метрику Delta E для точности цветопередачи.

### ✨ Возможности
- Рекурсивная обработка папок.
- Извлечение, сжатие и визуализация палитры (PNG).
- Поддержка форматов: HEX, webcolors, XKCD.
- Специальный режим для T5/ML (пробелы в названиях).
- Многопроцессорность для ускорения.

### 🛠 Установка
```bash
git clone https://github.com/vasiliypavlov/extract-color.git
cd extract-color
pip install -r requirements.txt
```

### 🚀 Использование
```bash
python extract_color.py [путь_к_папке_или_файлу] [опции]
```

**Основные флаги:**
- `-c N` — количество цветов (по умолчанию: 8).
- `-d N` — сжатие палитры в N раз.
- `-XKCD` — генерация названий для T5 (с пробелами).
- `-webcolors` — использование CSS3 палитры.
- `-separate` — отдельные файлы для каждого изображения.
- `-textonly` — только текстовый отчет (без PNG).

### ⚙ Технические детали
- **CIELAB & Delta E**: Точное сопоставление цветов.
- **Fastoctree**: Быстрое квантование (лого, иллюстрации).
- **KMeans**: Точное квантование для фото.

### 📄 Лицензия
MIT.

---

## English Version

**Color Palette Extractor** is a CLI tool for recursively extracting dominant colors from images. It supports quantization (`fastoctree`, `mediancut`, `kmeans`), hue grouping, PNG tile generation, and export to HEX, webcolors, or the extended **XKCD palette (949 colors)**, optimized for text encoders (T5, BERT). Uses the CIELAB color space and Delta E metric for accurate color matching.

### ✨ Features
- Recursive folder processing.
- Palette extraction, compression, and visualization (PNG).
- Output formats: HEX, webcolors, XKCD.
- Special mode for T5/ML (space-separated names).
- Multiprocessing for speed.

### 🛠 Installation
```bash
git clone https://github.com/vasiliypavlov/extract-color.git
cd extract-color
pip install -r requirements.txt
```

### 🚀 Usage
```bash
python extract_color.py [path_to_folder_or_file] [options]
```

**Key Flags:**
- `-c N` — number of colors (default: 8).
- `-d N` — compress palette by a factor of N.
- `-XKCD` — generate names for T5 (space-separated).
- `-webcolors` — use CSS3 palette.
- `-separate` — separate files per image.
- `-textonly` — text-only report (no PNG).

### ⚙ Technical Details
- **CIELAB & Delta E**: Accurate color matching.
- **Fastoctree**: Fast quantization (logos, illustrations).
- **KMeans**: Precise quantization for photos.

### 📄 License
MIT.
