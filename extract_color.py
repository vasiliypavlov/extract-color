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

# Optional XKCD palette dependency
try:
    import matplotlib.colors as mcolors
    XKCD_AVAILABLE = True
except ImportError:
    XKCD_AVAILABLE = False

# Variables / Переменные
ENV_DIR_VAR = "IMG_SCAN_DIR"
ENV_COLORS_VAR = "IMG_COLORS_COUNT"
DEFAULT_COLORS = 8
TILE_SIZE = 50
MERGE_THRESHOLD = 900

# Global variables for palette
LAB_PALETTE = {}
USE_XKCD = False

# --- Helper Functions / Вспомогательные функции ---

def print_help(lang):
    """Выводит справку на основе локали / Prints help based on locale"""
    if lang.startswith('ru'):
        print("Использование: python extract_color.py [путь] [опции]")
        print("\nОписание:")
        print("  Сканирует папку или файл, извлекает основные цвета, группирует их по оттенкам,")
        print("  создает текстовые файлы и изображения-плитки (квадрат 1:1).")
        print("  Режим '-webcolors' создает файл с чистыми CSS3 названиями (без адаптации).")
        print("  Режим '-XKCD' создает файл с 949 названиями XKCD, идеально подходит для T5 (разбиты пробелами).")
        print("  Для точности подбора названий используется CIELAB (Lab) и метрика Delta E.")
        print("\nАргументы:")
        print("  path                  Путь к папке или изображению (или переменная IMG_SCAN_DIR).")
        print("\nОпции:")
        print("  -summary              Создать один общий файл отчета (по умолчанию).")
        print("  -separate             Создать отдельные .txt/.png файлы для каждого изображения.")
        print("  -c N                  Количество извлекаемых цветов (по умолчанию: 8).")
        print("  -d N                  Сжимает палитру в N раз, сохраняя уникальные цвета.")
        print("  -method M             Метод извлечения: mediancut, fastoctree, kmeans.")
        print("  -webcolors            Создает файл webcolors_[имя].txt (CSS3, 140 цветов).")
        print("  -XKCD                 Создает файл XKCD_[имя].txt (949 цветов, требует matplotlib).")
        print("  -textonly             Отключить создание изображений-плиток PNG.")
        print("  -no-mp                Отключить многопроцессорность (для отладки или специфических сред).")
        print("  -h, --help            Показать эту справку.")
    else:
        print("Usage: python extract_color.py [path] [options]")
        print("\nDescription:")
        print("  Scans a folder or file, extracts main colors, groups them by hue,")
        print("  creates text files and tile images (1:1).")
        print("  '-webcolors' mode creates a file with raw CSS3 names (no adaptation).")
        print("  '-XKCD' mode creates a file with 949 XKCD names, perfect for T5 (spaced).")
        print("  Color naming accuracy is ensured by CIELAB (Lab) color space and Delta E metric.")
        print("\nArguments:")
        print("  path                  Path to folder or image (or env var IMG_SCAN_DIR).")
        print("\nOptions:")
        print("  -summary              Create a single general report file (default).")
        print("  -separate             Create individual .txt/.png files for each image.")
        print("  -c N                  Number of colors to extract (default: 8).")
        print("  -d N                  Compresses the palette N times, preserving unique colors.")
        print("  -method M             Extraction method: mediancut, fastoctree, kmeans.")
        print("  -webcolors            Creates webcolors_[name].txt file (CSS3, 140 colors).")
        print("  -XKCD                 Creates XKCD_[name].txt file (949 colors, requires matplotlib).")
        print("  -textonly             Disable generating PNG tile images.")
        print("  -no-mp                Disable multiprocessing (for debugging or specific environments).")
        print("  -h, --help            Show this help message.")

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def get_names_hex_source(use_xkcd):
    """Returns the color dictionary based on the flag, requiring proper libraries."""
    if use_xkcd:
        if not XKCD_AVAILABLE:
            print("Error: The -XKCD flag was used, but 'matplotlib' is not installed. Please install it with: pip install matplotlib")
            sys.exit(1)
        try:
            # Преобразуем HEX к нижнему регистру для единообразия
            xkcd_dict = {}
            for k, v in mcolors.XKCD_COLORS.items():
                hex_key = v.lower()
                name = k.replace('xkcd:', '')
                xkcd_dict[hex_key] = name
            if len(xkcd_dict) > 0:
                return xkcd_dict
            else:
                print("Error: XKCD palette is empty.")
                sys.exit(1)
        except Exception as e:
            print(f"Error: Failed to load XKCD palette: {e}")
            sys.exit(1)

    if webcolors is not None:
        try:
            if hasattr(webcolors, 'names') and hasattr(webcolors, 'name_to_hex'):
                d = {}
                for name in webcolors.names(spec='css3'):
                    d[webcolors.name_to_hex(name, spec='css3').lower()] = name
                return d
            elif hasattr(webcolors, 'CSS3_HEX_TO_NAMES'):
                return {k.lower(): v for k, v in webcolors.CSS3_HEX_TO_NAMES.items()}
        except:
            pass

    print("Error: Please install 'webcolors' for CSS3 mode or 'matplotlib' for XKCD mode.")
    sys.exit(1)

def init_lab_palette(source_dict):
    """Precompute LAB coordinates for all colors once."""
    palette = {}
    if not source_dict:
        return palette
    for hex_val, name in source_dict.items():
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
        for name, (lab, rgb) in LAB_PALETTE.items():
            distance = (rgb[0] - target_rgb[0])**2 + (rgb[1] - target_rgb[1])**2 + (rgb[2] - target_rgb[2])**2
            if distance < min_dist:
                min_dist = distance
                closest_name = name
    return closest_name

def get_color_name_only(hex_code):
    """Returns ONLY the color name (raw CSS3 or XKCD)."""
    try:
        rgb = tuple(int(hex_code.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        return get_cielab_closest_color(rgb)
    except:
        return hex_code

def get_unique_t5_names(colors):
    """Returns unique color names preserving order."""
    unique_names = []
    for c in colors:
        name = get_color_name_only(c)
        if name not in unique_names:
            unique_names.append(name)
    return unique_names

def get_hex_only(hex_code):
    return hex_code

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

# --- Multiprocessing Workers ---

def process_image_worker(args):
    image_path, num_colors, divisor, method = args
    palette = get_main_hex_colors(image_path, num_colors, method)
    if palette:
        palette = sort_colors_by_hue(palette)
        palette = compress_palette(palette, divisor)
        return os.path.basename(image_path), palette
    return None

# --- Main Logic ---

def process_single_file(image_path, summary_mode, num_colors, generate_images, divisor, method, generate_names):
    palette = get_main_hex_colors(image_path, num_colors, method)
    if not palette: return
    palette = sort_colors_by_hue(palette)
    palette = compress_palette(palette, divisor)
    
    hex_string = ", ".join([get_hex_only(c) for c in palette])
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
        if generate_names:
            names_string = ", ".join(get_unique_t5_names(palette))
            wc_output_filename = f"XKCD_palette_image_{filename}.txt" if USE_XKCD else f"webcolors_palette_image_{filename}.txt"
            wc_output_path = os.path.join(os.getcwd(), wc_output_filename)
            with open(wc_output_path, 'w', encoding='utf-8') as f:
                f.write(names_string)
            print(f"Created names report: {wc_output_path}")
        if generate_images:
            generate_palette_image(palette, os.path.join(os.getcwd(), f"color_palette_image_{filename}.png"))
    else:
        base_name = os.path.splitext(filename)[0]
        txt_path = os.path.join(os.path.dirname(image_path), f"{base_name}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(hex_string)
        if generate_names:
            names_string = ", ".join(get_unique_t5_names(palette))
            wc_txt_path = os.path.join(os.path.dirname(image_path), f"XKCD_palette_{base_name}.txt" if USE_XKCD else f"webcolors_palette_{base_name}.txt")
            with open(wc_txt_path, 'w', encoding='utf-8') as f:
                f.write(names_string)
            print(f"Created names file: {wc_txt_path}")
        if generate_images:
            generate_palette_image(palette, os.path.join(os.path.dirname(image_path), f"{base_name}.png"))

def process_folder(folder_path, summary_mode, num_colors, generate_images, divisor, method, use_multiprocessing, generate_names):
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
        
        if generate_names:
            wc_output_filename = f"XKCD_palette_folder_{folder_name}.txt" if USE_XKCD else f"webcolors_palette_folder_{folder_name}.txt"
            wc_output_path = os.path.join(os.getcwd(), wc_output_filename)
            with open(wc_output_path, 'w', encoding='utf-8') as f:
                f.write(", ".join(get_unique_t5_names(folder_unique_colors)))
            print(f"Created names report: {wc_output_path}")
            
        if generate_images:
            generate_palette_image(folder_unique_colors, os.path.join(os.getcwd(), f"color_palette_folder_{folder_name}.png"))
    else:
        for filename, palette in all_palettes.items():
            original_path = [p for p in image_files if os.path.basename(p) == filename][0]
            base_name = os.path.splitext(os.path.basename(original_path))[0]
            txt_path = os.path.join(os.path.dirname(original_path), f"{base_name}.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(", ".join([get_hex_only(c) for c in palette]))
            if generate_names:
                wc_txt_path = os.path.join(os.path.dirname(original_path), f"XKCD_palette_{base_name}.txt" if USE_XKCD else f"webcolors_palette_{base_name}.txt")
                with open(wc_txt_path, 'w', encoding='utf-8') as f:
                    f.write(", ".join(get_unique_t5_names(palette)))
                print(f"Created names file: {wc_txt_path}")
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
    parser.add_argument("-webcolors", action="store_true", help="Creates webcolors_[name].txt file (CSS3, 140 colors).")
    parser.add_argument("-XKCD", action="store_true", help="Creates XKCD_[name].txt file (949 colors, requires matplotlib).")

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

    USE_XKCD = args.XKCD
    generate_names = args.webcolors or args.XKCD

    # Инициализация палитры выполняется только если запрошены текстовые имена цветов
    if generate_names:
        source_dict = get_names_hex_source(USE_XKCD)
        LAB_PALETTE = init_lab_palette(source_dict)

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
        process_folder(input_path, is_summary_mode, num_colors, generate_images, args.divisor, args.method, use_mp, generate_names)
    elif os.path.isfile(input_path):
        process_single_file(input_path, is_summary_mode, num_colors, generate_images, args.divisor, args.method, generate_names)
    else:
        print("Error: Invalid path.")
        sys.exit(1)
