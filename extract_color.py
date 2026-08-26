import os
import sys
import argparse
import math
import colorsys
import multiprocessing
from PIL import Image, ImageDraw

# Optional dependencies / Опциональные зависимости
try:
    import webcolors
except ImportError:
    webcolors = None

try:
    import numpy as np
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from skimage.color import rgb2lab, deltaE_cie76
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False

# Variables / Переменные
ENV_DIR_VAR = "IMG_SCAN_DIR"
ENV_COLORS_VAR = "IMG_COLORS_COUNT"
DEFAULT_COLORS = 8
TILE_SIZE = 50
MERGE_THRESHOLD = 900

# --- T5 Friendly Name Mapping ---
T5_COLOR_NAMES_MAP = {
    "aliceblue": "alice blue", "antiquewhite": "antique white", "aquamarine": "aquamarine",
    "blanchedalmond": "blanched almond", "blueviolet": "blue violet", "burlywood": "burly wood",
    "cadetblue": "cadet blue", "cornflowerblue": "cornflower blue", "cornsilk": "cornsilk",
    "darkblue": "dark blue", "darkcyan": "dark cyan", "darkgoldenrod": "dark goldenrod",
    "darkgray": "dark gray", "darkgreen": "dark green", "darkkhaki": "dark khaki",
    "darkmagenta": "dark magenta", "darkolivegreen": "dark olive green", "darkorange": "dark orange",
    "darkorchid": "dark orchid", "darkred": "dark red", "darksalmon": "dark salmon",
    "darkseagreen": "dark sea green", "darkslateblue": "dark slate blue", "darkslategray": "dark slate gray",
    "darkturquoise": "dark turquoise", "darkviolet": "dark violet", "deeppink": "deep pink",
    "deepskyblue": "deep sky blue", "dimgray": "dim gray", "dodgerblue": "dodger blue",
    "firebrick": "fire brick", "floralwhite": "floral white", "forestgreen": "forest green",
    "gainsboro": "gainsboro", "ghostwhite": "ghost white", "goldenrod": "golden rod",
    "greenyellow": "green yellow", "honeydew": "honeydew", "hotpink": "hot pink",
    "indianred": "indian red", "lavenderblush": "lavender blush", "lawngreen": "lawn green",
    "lemonchiffon": "lemon chiffon", "lightblue": "light blue", "lightcoral": "light coral",
    "lightcyan": "light cyan", "lightgoldenrodyellow": "light goldenrod yellow", "lightgray": "light gray",
    "lightgreen": "light green", "lightpink": "light pink", "lightsalmon": "light salmon",
    "lightseagreen": "light sea green", "lightskyblue": "light sky blue", "lightslategray": "light slate gray",
    "lightsteelblue": "light steel blue", "lightyellow": "light yellow", "limegreen": "lime green",
    "mediumaquamarine": "medium aquamarine", "mediumblue": "medium blue", "mediumorchid": "medium orchid",
    "mediumpurple": "medium purple", "mediumseagreen": "medium sea green", "mediumslateblue": "medium slate blue",
    "mediumspringgreen": "medium spring green", "mediumturquoise": "medium turquoise",
    "mediumvioletred": "medium violet red", "midnightblue": "midnight blue", "mintcream": "mint cream",
    "mistyrose": "misty rose", "moccasin": "moccasin", "navajowhite": "navajo white",
    "oldlace": "old lace", "olivedrab": "olive drab", "orangered": "orange red",
    "palegoldenrod": "pale goldenrod", "palegreen": "pale green", "paleturquoise": "pale turquoise",
    "palevioletred": "pale violet red", "papayawhip": "papaya whip", "peachpuff": "peach puff",
    "powderblue": "powder blue", "rebeccapurple": "rebecca purple", "rosybrown": "rosy brown",
    "royalblue": "royal blue", "saddlebrown": "saddle brown", "sandybrown": "sandy brown",
    "seagreen": "sea green", "seashell": "seashell", "skyblue": "sky blue",
    "slateblue": "slate blue", "slategray": "slate gray", "springgreen": "spring green",
    "steelblue": "steel blue", "tomato": "tomato", "turquoise": "turquoise",
    "whitesmoke": "white smoke", "yellowgreen": "yellow green"
}

def format_t5_name(name):
    """Converts CSS3 names to T5 friendly spaced names."""
    return T5_COLOR_NAMES_MAP.get(name, name)

# --- Embedded Color Dictionary (140 CSS3 colors) ---
FALLBACK_CSS3_HEX_TO_NAMES = {
    '#000000': 'black', '#000080': 'navy', '#00008b': 'darkblue', '#0000cd': 'mediumblue',
    '#0000ff': 'blue', '#006400': 'darkgreen', '#008000': 'green', '#008080': 'teal',
    '#008b8b': 'darkcyan', '#00bfff': 'deepskyblue', '#00ced1': 'darkturquoise',
    '#00fa9a': 'mediumspringgreen', '#00ff00': 'lime', '#00ff7f': 'springgreen',
    '#00ffff': 'cyan', '#191970': 'midnightblue', '#1e90ff': 'dodgerblue',
    '#20b2aa': 'lightseagreen', '#228b22': 'forestgreen', '#2e8b57': 'seagreen',
    '#2f4f4f': 'darkslategray', '#32cd32': 'limegreen', '#3cb371': 'mediumseagreen',
    '#40e0d0': 'turquoise', '#4169e1': 'royalblue', '#4682b4': 'steelblue',
    '#483d8b': 'darkslateblue', '#48d1cc': 'mediumturquoise', '#4b0082': 'indigo',
    '#556b2f': 'darkolivegreen', '#5f9ea0': 'cadetblue', '#6495ed': 'cornflowerblue',
    '#66cdaa': 'mediumaquamarine', '#696969': 'dimgray', '#6a5acd': 'slateblue',
    '#6b8e23': 'olivedrab', '#708090': 'slategray', '#778899': 'lightslategray',
    '#7b68ee': 'mediumslateblue', '#7cfc00': 'lawngreen', '#7fff00': 'chartreuse',
    '#800000': 'maroon', '#800080': 'purple', '#808000': 'olive', '#808080': 'gray',
    '#87ceeb': 'skyblue', '#87cefa': 'lightskyblue', '#8a2be2': 'blueviolet',
    '#8b0000': 'darkred', '#8b008b': 'darkmagenta', '#8b4513': 'saddlebrown',
    '#98fb98': 'palegreen', '#9acd32': 'yellowgreen', '#a0522d': 'sienna',
    '#a52a2a': 'brown', '#a9a9a9': 'darkgray', '#add8e6': 'lightblue', '#adff2f': 'greenyellow',
    '#afeeee': 'paleturquoise', '#b0c4de': 'lightsteelblue', '#b0e0e6': 'powderblue',
    '#b22222': 'firebrick', '#b8860b': 'darkgoldenrod', '#ba55d3': 'mediumorchid',
    '#bc8f8f': 'rosybrown', '#bdb76b': 'darkkhaki', '#c0c0c0': 'silver',
    '#c71585': 'mediumvioletred', '#cd5c5c': 'indianred', '#cd853f': 'peru',
    '#d2691e': 'chocolate', '#d3d3d3': 'lightgray', '#d8bfd8': 'thistle',
    '#da70d6': 'orchid', '#daa520': 'goldenrod', '#db7093': 'palevioletred',
    '#dc143c': 'crimson', '#dda0dd': 'plum', '#deb887': 'burlywood',
    '#e0ffff': 'lightcyan', '#e6e6fa': 'lavender', '#e9967a': 'darksalmon',
    '#ee82ee': 'violet', '#eee8aa': 'palegoldenrod', '#f0e68c': 'khaki',
    '#f0f8ff': 'aliceblue', '#f0fff0': 'honeydew', '#f5deb3': 'wheat',
    '#f5f5dc': 'beige', '#f5f5f5': 'whitesmoke', '#faf0e6': 'linen',
    '#fafad2': 'lightgoldenrodyellow', '#fdf5e6': 'oldlace', '#ff0000': 'red',
    '#ff00ff': 'magenta', '#ff1493': 'deeppink', '#ff4500': 'orangered',
    '#ff6347': 'tomato', '#ff69b4': 'hotpink', '#ff7f50': 'coral',
    '#ff8c00': 'darkorange', '#ffa500': 'orange', '#ffa07a': 'lightsalmon',
    '#ffb6c1': 'lightpink', '#ffc0cb': 'pink', '#ffd700': 'gold',
    '#ffdead': 'navajowhite', '#ffebcd': 'blanchedalmond', '#ffefd5': 'papayawhip',
    '#fff0f5': 'lavenderblush', '#fff5ee': 'seashell', '#fff8dc': 'cornsilk',
    '#fffacd': 'lemonchiffon', '#fffafa': 'snow', '#ffff00': 'yellow',
    '#ffffe0': 'lightyellow', '#fffff0': 'ivory', '#ffffff': 'white'
}

def get_names_hex_source():
    """Returns the color dictionary (either from webcolors or fallback)."""
    if webcolors is not None:
        try:
            if hasattr(webcolors, 'CSS3_HEX_TO_NAMES'):
                return webcolors.CSS3_HEX_TO_NAMES
            elif hasattr(webcolors, 'names') and hasattr(webcolors, 'name_to_hex'):
                d = {}
                for name in webcolors.names(spec='css3'):
                    d[webcolors.name_to_hex(name, spec='css3')] = name
                return d
        except:
            pass
    return FALLBACK_CSS3_HEX_TO_NAMES

# --- CIELAB Initialization ---
def init_lab_palette():
    """Precompute LAB coordinates for all colors once."""
    palette = {}
    names_hex = get_names_hex_source()
    for hex_val, name in names_hex.items():
        try:
            rgb = tuple(int(hex_val.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            if SKIMAGE_AVAILABLE:
                rgb_norm = [[[rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0]]]
                lab = rgb2lab(rgb_norm)[0][0]
                palette[name] = (lab, rgb)
            else:
                palette[name] = (None, rgb)
        except:
            continue
    return palette

LAB_PALETTE = init_lab_palette()

def get_cielab_closest_color(target_rgb):
    """Finds closest color name using CIELAB deltaE (human perception)."""
    min_dist = float('inf')
    closest_name = "unknown"
    
    if SKIMAGE_AVAILABLE:
        target_norm = [[[target_rgb[0]/255.0, target_rgb[1]/255.0, target_rgb[2]/255.0]]]
        target_lab = rgb2lab(target_norm)[0][0]
        for name, (lab, rgb) in LAB_PALETTE.items():
            if lab is None: continue
            distance = deltaE_cie76(target_lab, lab)
            if distance < min_dist:
                min_dist = distance
                closest_name = name
    else:
        # Fallback to RGB distance
        for name, (lab, rgb) in LAB_PALETTE.items():
            distance = (rgb[0] - target_rgb[0])**2 + (rgb[1] - target_rgb[1])**2 + (rgb[2] - target_rgb[2])**2
            if distance < min_dist:
                min_dist = distance
                closest_name = name
    return closest_name

def get_hex_only(hex_code):
    """Returns ONLY the HEX code (for the main palette file)."""
    return hex_code

def get_color_name_only(hex_code):
    """Returns ONLY T5 friendly name (no HEX) for -webcolors mode."""
    try:
        rgb = tuple(int(hex_code.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        return format_t5_name(get_cielab_closest_color(rgb))
    except:
        return hex_code

def get_unique_t5_names(colors):
    """Returns unique T5 names preserving order."""
    unique_names = []
    for c in colors:
        name = get_color_name_only(c)
        if name not in unique_names:
            unique_names.append(name)
    return unique_names

# --- Helper Functions ---
def print_help(lang):
    if lang.startswith('ru'):
        print("Использование: python extract_color.py [путь] [опции]")
        print("\nОписание:")
        print("  Сканирует папку или файл, извлекает основные цвета, группирует их по оттенкам,")
        print("  создает текстовые файлы и изображения-плитки (квадрат 1:1).")
        print("  Режим '-webcolors' генерирует отдельный файл, содержащий ТОЛЬКО уникальные")
        print("  названия цветов без HEX-кодов. Это идеально подходит для передачи в текстовые")
        print("  энкодеры (например, T5) для генеративных моделей.")
        print("  Для максимальной точности подбора названий скрипт использует цветовое")
        print("  пространство CIELAB (Lab) и метрику Delta E (расстояние с учетом восприятия")
        print("  человеческим глазом). Названия автоматически преобразуются в удобный для")
        print("  токенизаторов вид: сложные имена разбиваются пробелами (например,")
        print("  'darkslategray' -> 'dark slate gray').")
        print("\nАргументы:")
        print("  path                  Путь к папке или изображению (или переменная IMG_SCAN_DIR).")
        print("\nОпции:")
        print("  -summary              Создать один общий файл отчета (по умолчанию).")
        print("  -separate             Создать отдельные .txt/.png файлы для каждого изображения.")
        print("  -c N                  Количество извлекаемых цветов (по умолчанию: 8).")
        print("  -d N                  Сжимает палитру в N раз, сохраняя уникальные цвета.")
        print("  -method M             Метод извлечения: mediancut, fastoctree, kmeans.")
        print("  -webcolors            Дополнительно создает файл только с названиями цветов (без HEX) для T5.")
        print("  -textonly             Отключить создание изображений-плиток PNG.")
        print("  -no-mp                Отключить многопроцессорность (для отладки или специфических сред).")
        print("  -h, --help            Показать эту справку.")
    else:
        print("Usage: python extract_color.py [path] [options]")
        print("\nDescription:")
        print("  Scans a folder or file, extracts main colors, groups them by hue,")
        print("  creates text files and tile images (1:1).")
        print("  The '-webcolors' mode generates a separate file containing ONLY unique")
        print("  color names (no HEX codes). This is perfect for feeding into text encoders")
        print("  (e.g., T5) for generative models.")
        print("  For maximum color naming accuracy, the script uses the CIELAB (Lab) color")
        print("  space and Delta E metric (calculating distance based on human perception).")
        print("  Names are automatically converted to tokenizer-friendly formats by splitting")
        print("  concatenated names with spaces (e.g., 'darkslategray' -> 'dark slate gray').")
        print("\nArguments:")
        print("  path                  Path to folder or image (or env var IMG_SCAN_DIR).")
        print("\nOptions:")
        print("  -summary              Create a single general report file (default).")
        print("  -separate             Create individual .txt/.png files for each image.")
        print("  -c N                  Number of colors to extract (default: 8).")
        print("  -d N                  Compresses the palette N times, preserving unique colors.")
        print("  -method M             Extraction method: mediancut, fastoctree, kmeans.")
        print("  -webcolors            Additionally creates a file with ONLY color names (no HEX) for T5.")
        print("  -textonly             Disable generating PNG tile images.")
        print("  -no-mp                Disable multiprocessing (for debugging or specific environments).")
        print("  -h, --help            Show this help message.")

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def get_hue_category(hex_color):
    r, g, b = [x / 255.0 for x in hex_to_rgb(hex_color)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h *= 360
    if v < 0.15: return "Black"
    if v > 0.9 and s < 0.1: return "White"
    if s < 0.15 and 0.15 <= v <= 0.9: return "Gray"
    if h < 15 or h >= 345: return "Red"
    if h < 40 and v < 0.6: return "Brown"
    if h < 45: return "Orange"
    if h < 70: return "Yellow"
    if h < 160: return "Green"
    if h < 200: return "Cyan"
    if h < 260: return "Blue"
    if h < 320: return "Purple"
    return "Pink"

def sort_colors_by_hue(colors):
    order = ["Red", "Orange", "Yellow", "Green", "Cyan", "Blue", "Purple", "Pink", "Brown", "Gray", "Black", "White"]
    color_groups = {}
    for c in colors:
        cat = get_hue_category(c)
        color_groups.setdefault(cat, []).append(c)
    
    sorted_colors = []
    for cat in order:
        if cat in color_groups:
            color_groups[cat].sort(key=lambda c: colorsys.rgb_to_hsv(*[x/255 for x in hex_to_rgb(c)])[2], reverse=True)
            sorted_colors.extend(color_groups[cat])
    return sorted_colors

def rgb_distance(c1, c2):
    return sum((a - b) ** 2 for a, b in zip(c1, c2))

def compress_palette(colors, divisor):
    if divisor <= 1:
        return colors
    target_len = max(1, math.ceil(len(colors) / divisor))
    if len(colors) <= target_len:
        return colors

    current_colors = [hex_to_rgb(c) for c in colors]
    while len(current_colors) > target_len:
        min_dist = float('inf')
        merge_idx = (0, 1)
        for i in range(len(current_colors)):
            for j in range(i + 1, len(current_colors)):
                dist = rgb_distance(current_colors[i], current_colors[j])
                if dist < min_dist:
                    min_dist = dist
                    merge_idx = (i, j)
        if min_dist > MERGE_THRESHOLD:
            break
        c1 = current_colors[merge_idx[0]]
        c2 = current_colors[merge_idx[1]]
        merged = tuple((a + b) // 2 for a, b in zip(c1, c2))
        del current_colors[merge_idx[1]]
        del current_colors[merge_idx[0]]
        current_colors.append(merged)
    return [rgb_to_hex(c) for c in current_colors]

def generate_palette_image(colors, output_path):
    if not colors:
        return
    side = math.ceil(math.sqrt(len(colors)))
    if side < 2:
        side = 2
    width = height = side * TILE_SIZE
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    for i, color in enumerate(colors):
        rgb = hex_to_rgb(color)
        x = (i % side) * TILE_SIZE
        y = (i // side) * TILE_SIZE
        draw.rectangle([x, y, x + TILE_SIZE - 1, y + TILE_SIZE - 1], fill=rgb)
    img.save(output_path)

def get_main_hex_colors(image_path, num_colors, method="fastoctree"):
    try:
        img = Image.open(image_path).convert('RGB')
        img.thumbnail((150, 150))
        if method == "kmeans":
            if not SKLEARN_AVAILABLE:
                print("  Warning: scikit-learn not installed. Falling back to fastoctree.")
                method = "fastoctree"
            else:
                pixels = np.array(img).reshape(-1, 3).astype(float)
                kmeans = KMeans(n_clusters=num_colors, n_init=5, random_state=42).fit(pixels)
                centers = kmeans.cluster_centers_.astype(int)
                return [rgb_to_hex(tuple(c)) for c in centers[:num_colors]]
        if method == "mediancut":
            quant_method = Image.Quantize.MEDIANCUT
        elif method == "fastoctree":
            quant_method = Image.Quantize.FASTOCTREE
        else:
            quant_method = Image.Quantize.FASTOCTREE
        quantized = img.quantize(colors=num_colors, method=quant_method, dither=Image.NONE)
        palette = quantized.getpalette()
        if not palette:
            return []
        hex_colors = []
        for i in range(0, len(palette), 3):
            hex_colors.append(f"#{palette[i]:02x}{palette[i+1]:02x}{palette[i+2]:02x}")
        return hex_colors[:num_colors]
    except Exception as e:
        print(f"   Error processing {image_path}: {e}")
        return []

def get_unique_colors_from_all_palettes(all_palettes):
    unique_colors = set()
    for palette in all_palettes.values():
        for color in palette:
            unique_colors.add(color)
    return list(unique_colors)

def process_image_worker(args):
    image_path, num_colors, divisor, method = args
    palette = get_main_hex_colors(image_path, num_colors, method)
    if palette:
        palette = sort_colors_by_hue(palette)
        palette = compress_palette(palette, divisor)
        return os.path.basename(image_path), palette
    return None

# --- Main Logic ---
def process_single_file(image_path, summary_mode, num_colors, generate_images, divisor, method, generate_webcolors):
    palette = get_main_hex_colors(image_path, num_colors, method)
    if not palette: return
    palette = sort_colors_by_hue(palette)
    palette = compress_palette(palette, divisor)
    
    # Только чистый HEX
    hex_string = ", ".join([get_hex_only(c) for c in palette])
    # Только чистые имена для T5
    webcolors_string = ", ".join(get_unique_t5_names(palette))
    
    filename = os.path.basename(image_path)

    if summary_mode:
        output_filename = f"color_palette_image_{filename}.txt"
        output_path = os.path.join(os.getcwd(), output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Unique colors for this image:\n")
            f.write(hex_string + "\n\n")
            f.write("Per-image colors:\n")
            f.write(f"{filename}: {hex_string}")
        print(f"Created report: {output_path}")
        if generate_webcolors:
            wc_output_filename = f"webcolors_palette_image_{filename}.txt"
            wc_output_path = os.path.join(os.getcwd(), wc_output_filename)
            with open(wc_output_path, 'w', encoding='utf-8') as f:
                f.write(webcolors_string)
            print(f"Created webcolors report: {wc_output_path}")
        if generate_images:
            generate_palette_image(palette, os.path.join(os.getcwd(), f"color_palette_image_{filename}.png"))
    else:
        base_name = os.path.splitext(filename)[0]
        txt_path = os.path.join(os.path.dirname(image_path), f"{base_name}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(hex_string)
        if generate_webcolors:
            wc_txt_path = os.path.join(os.path.dirname(image_path), f"webcolors_palette_{base_name}.txt")
            with open(wc_txt_path, 'w', encoding='utf-8') as f:
                f.write(webcolors_string)
            print(f"Created webcolors file: {wc_txt_path}")
        if generate_images:
            generate_palette_image(palette, os.path.join(os.path.dirname(image_path), f"{base_name}.png"))

def process_folder(folder_path, summary_mode, num_colors, generate_images, divisor, method, use_multiprocessing, generate_webcolors):
    extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff')
    image_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(extensions):
                image_files.append(os.path.join(root, file))
    if not image_files:
        print("No images found in folder.")
        return

    args = [(path, num_colors, divisor, method) for path in image_files]
    results = []
    if use_multiprocessing:
        try:
            print(f"Processing {len(image_files)} images with multiprocessing...")
            with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
                results = pool.map(process_image_worker, args)
        except Exception as e:
            print(f"Warning: Multiprocessing failed ({e}). Falling back to sequential processing.")
            results = [process_image_worker(a) for a in args]
    else:
        print(f"Processing {len(image_files)} images sequentially...")
        results = [process_image_worker(a) for a in args]

    all_palettes = {}
    for res in results:
        if res:
            all_palettes[res[0]] = res[1]
    if not all_palettes: return

    if summary_mode:
        folder_unique_colors = get_unique_colors_from_all_palettes(all_palettes)
        folder_unique_colors = sort_colors_by_hue(folder_unique_colors)
        folder_unique_colors = compress_palette(folder_unique_colors, divisor)
        
        folder_name = os.path.basename(os.path.normpath(folder_path))
        output_filename = f"color_palette_folder_{folder_name}.txt"
        output_path = os.path.join(os.getcwd(), output_filename)
        
        print(f"Writing summary report to {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Unique colors for the entire folder:\n")
            f.write(", ".join([get_hex_only(c) for c in folder_unique_colors]) + "\n\n")
            f.write("Per-image colors:\n")
            for filename, palette in all_palettes.items():
                f.write(f"{filename}: {', '.join([get_hex_only(c) for c in palette])}\n")
        
        if generate_webcolors:
            wc_output_filename = f"webcolors_palette_folder_{folder_name}.txt"
            wc_output_path = os.path.join(os.getcwd(), wc_output_filename)
            with open(wc_output_path, 'w', encoding='utf-8') as f:
                f.write(", ".join(get_unique_t5_names(folder_unique_colors)))
            print(f"Created webcolors report: {wc_output_path}")
            
        if generate_images:
            generate_palette_image(folder_unique_colors, os.path.join(os.getcwd(), f"color_palette_folder_{folder_name}.png"))
    else:
        for filename, palette in all_palettes.items():
            original_path = [p for p in image_files if os.path.basename(p) == filename][0]
            base_name = os.path.splitext(os.path.basename(original_path))[0]
            txt_path = os.path.join(os.path.dirname(original_path), f"{base_name}.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(", ".join([get_hex_only(c) for c in palette]))
            if generate_webcolors:
                wc_txt_path = os.path.join(os.path.dirname(original_path), f"webcolors_palette_{base_name}.txt")
                with open(wc_txt_path, 'w', encoding='utf-8') as f:
                    f.write(", ".join(get_unique_t5_names(palette)))
                print(f"Created webcolors file: {wc_txt_path}")
            if generate_images:
                generate_palette_image(palette, os.path.join(os.path.dirname(original_path), f"{base_name}.png"))

# --- Main Entry Point ---
if __name__ == "__main__":
    current_lang = os.environ.get('LANG', 'en_US.UTF-8')
    if len(sys.argv) == 1:
        print_help(current_lang)
        sys.exit(0)

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("input_path", nargs="?", help="Path to folder or single image.")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("-summary", action="store_true", help="Create a single general report file (default).")
    mode_group.add_argument("-separate", action="store_true", help="Create individual .txt files for each image.")
    parser.add_argument("-textonly", action="store_true", help="Disable creating PNG tile images.")
    parser.add_argument("-no-mp", "--no-multiprocessing", action="store_true", help="Disable multiprocessing (useful for debugging or specific environments).")
    parser.add_argument("-c", "--colors", type=int, default=None, help=f"Number of colors to extract (default: {DEFAULT_COLORS})")
    parser.add_argument("-d", "--divisor", type=int, default=1, help="Compress palette N times, preserving unique colors.")
    parser.add_argument("-method", type=str, choices=['mediancut', 'fastoctree', 'kmeans'], default='fastoctree', help="Extraction method (default: fastoctree)")
    parser.add_argument("-webcolors", action="store_true", help="Additionally creates a file with ONLY color names (no HEX) for T5.")

    try:
        args = parser.parse_args()
    except SystemExit:
        sys.exit(0)

    input_path = args.input_path
    if not input_path:
        input_path = os.environ.get(ENV_DIR_VAR)
        if not input_path:
            print_help(current_lang)
            sys.exit(1)

    is_summary_mode = not args.separate
    generate_images = not args.textonly
    use_mp = not args.no_multiprocessing

    if args.colors is not None:
        num_colors = args.colors
    else:
        env_colors = os.environ.get(ENV_COLORS_VAR)
        if env_colors and env_colors.isdigit():
            num_colors = int(env_colors)
        else:
            num_colors = DEFAULT_COLORS

    if not os.path.exists(input_path):
        print(f"Error: Path '{input_path}' does not exist.")
        sys.exit(1)

    if os.path.isdir(input_path):
        process_folder(input_path, is_summary_mode, num_colors, generate_images, args.divisor, args.method, use_mp, args.webcolors)
    elif os.path.isfile(input_path):
        process_single_file(input_path, is_summary_mode, num_colors, generate_images, args.divisor, args.method, args.webcolors)
    else:
        print("Error: Invalid path.")
        sys.exit(1)