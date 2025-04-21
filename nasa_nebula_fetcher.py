import requests
from PIL import Image
from io import BytesIO
import re
import datetime
import pyneb as pn
from astroquery.simbad import Simbad
from astroquery.vizier import Vizier

# Catálogo de nebulosas populares
CATALOGO_NEBULOSAS = {
    1: "Helix Nebula",
    2: "Cat's Eye Nebula",
    3: "Ring Nebula",
    4: "Dumbbell Nebula",
    5: "Eskimo Nebula",
    6: "Saturn Nebula",
    7: "NGC 7027",
    8: "NGC 6543",
    9: "IC 418",
    10: "NGC 3242"
}

MAPEAMENTO_SIMBAD = {
    "Cat's Eye Nebula": "NGC 6543",
    "Ring Nebula": "NGC 6720",
    "Eskimo Nebula": "NGC 2392",
    "Helix Nebula": "NGC 7293",
    "Dumbbell Nebula": "NGC 6853",
    "Saturn Nebula": "NGC 7009"
}

DADOS_FIXOS = {
    "NGC 6543": {"ra": "17 58 33.4", "dec": "+66 37 59", "dist_pc": 1001, "dist_ly": 3266.5},
    "NGC 6720": {"ra": "18 53 35.1", "dec": "+33 01 45", "dist_pc": 720, "dist_ly": 2350.3},
    "NGC 2392": {"ra": "07 29 10.8", "dec": "+20 54 42", "dist_pc": 870, "dist_ly": 2837.6}
}

COMPOSICAO_GENERICA = [
    ("Hidrogênio (Hα)", "656.3 nm", "vermelho"),
    ("Oxigênio duplamente ionizado [O III]", "495.9 nm e 500.7 nm", "verde-brilhante"),
    ("Hélio II", "468.6 nm", "azulado"),
    ("Nitrogênio ionizado [N II]", "658.4 nm", "vermelho-alaranjado")
]

def limpar_nome_arquivo(texto):
    return re.sub(r'[\\/*?:"<>|]', "_", texto.replace(" ", "_"))

def buscar_dados_simbad(nome_objeto):
    nome_query = MAPEAMENTO_SIMBAD.get(nome_objeto, nome_objeto)
    try:
        Simbad.TIMEOUT = 10
        Simbad.add_votable_fields("coordinates", "mesdistance")
        result = Simbad.query_object(nome_query)
        if result and "RA" in result.colnames and "DEC" in result.colnames:
            ra = result["RA"][0]
            dec = result["DEC"][0]
            dist_pc = result["Distance_distance"][0] if "Distance_distance" in result.colnames else None
            dist_ly = float(dist_pc) * 3.26156 if dist_pc else None
            return {"ra": ra, "dec": dec, "dist_pc": dist_pc, "dist_ly": dist_ly}
    except Exception as e:
        print(f"❌ Erro ao consultar SIMBAD: {e}")
    if nome_query in DADOS_FIXOS:
        print(f"🔁 Usando dados manuais confiáveis para: {nome_query}")
        return DADOS_FIXOS[nome_query]
    return None

def buscar_composicao_quimica(nome_query):
    vizier = Vizier(columns=["*"], column_filters={})
    vizier.ROW_LIMIT = 50
    try:
        resultado = vizier.query_object(nome_query)
        for tabela in resultado:
            for coluna in tabela.colnames:
                if "logOH" in coluna or "O_H" in coluna:
                    val = tabela[coluna][0]
                    return f"log(O/H) ≈ {val}"
    except Exception as e:
        print(f"⚠️ Erro ao consultar composição química em VizieR: {e}")
    return None

def calcular_condicoes_pyneb():
    O3 = pn.Atom('O', 3)
    N2 = pn.Atom('N', 2)
    S2 = pn.Atom('S', 2)

    flux_4959 = 100
    flux_5007 = 300
    flux_6548 = 30
    flux_6584 = 90
    flux_6716 = 40
    flux_6731 = 35
    flux_hbeta = 100

    ratio_O3 = (flux_4959 + flux_5007) / flux_hbeta
    ratio_N2 = (flux_6548 + flux_6584) / flux_hbeta
    ratio_S2 = flux_6716 / flux_6731

    temp_O3 = O3.getTemDen(ratio_O3, den=1000, wave1=5007, wave2=4959)
    temp_N2 = N2.getTemDen(ratio_N2, den=1000, wave1=6584, wave2=6548)
    ne_S2 = S2.getTemDen(ratio_S2, tem=temp_O3, wave1=6716, wave2=6731, den=None)

    return {
        "Temperatura [O III] (K)": temp_O3,
        "Temperatura [N II] (K)": temp_N2,
        "Densidade Eletrônica [S II] (cm⁻³)": ne_S2
    }

def salvar_info_em_txt(nome_nebulosa, dados_astro, imagens):
    nome_id = MAPEAMENTO_SIMBAD.get(nome_nebulosa, nome_nebulosa)
    arquivo_nome = f"{limpar_nome_arquivo(nome_nebulosa)}_info.txt"
    composicao_real = buscar_composicao_quimica(nome_id)
    condicoes_pyneb = calcular_condicoes_pyneb()

    with open(arquivo_nome, "w", encoding="utf-8") as f:
        f.write(f"Nebulosa: {nome_nebulosa}\n")
        if dados_astro:
            f.write(f"Coordenadas: RA = {dados_astro['ra']}, DEC = {dados_astro['dec']}\n")
            if dados_astro['dist_ly']:
                f.write(f"Distância estimada: {dados_astro['dist_ly']:.1f} anos-luz ({dados_astro['dist_pc']} pc)\n")
        else:
            f.write("Dados astronômicos indisponíveis.\n")

        f.write(f"Data: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("\nImagens baixadas:\n")
        for img in imagens:
            f.write(f"- {img}\n")

        f.write("\nLegenda científica sugerida:\n")
        if dados_astro and dados_astro['dist_ly']:
            f.write(f"Imagem da {nome_nebulosa}, localizada a aproximadamente {dados_astro['dist_ly']:.0f} anos-luz. RA: {dados_astro['ra']} | DEC: {dados_astro['dec']}.\n")
        else:
            f.write(f"Imagem da {nome_nebulosa}. Dados incompletos.\n")

        f.write("\nComposição química estimada:\n")
        if composicao_real:
            f.write(f"- {composicao_real} (extraída via VizieR)\n")
        else:
            for elem, linha, cor in COMPOSICAO_GENERICA:
                f.write(f"- {elem} ({linha}) - tonalidade: {cor}\n")

        f.write("\nCondições Físicas Simuladas (PyNeb):\n")
        for descricao, valor in condicoes_pyneb.items():
            f.write(f"- {descricao}: {valor:.0f} K\n")

    print(f"\n📝 Informações salvas em: {arquivo_nome}")

def search_nasa_images(query, max_results=10):
    query = query.replace("'", "").strip()
    print(f"\n🔭 Buscando imagens da NASA para: '{query}'")
    url = "https://images-api.nasa.gov/search"
    params = {"q": query, "media_type": "image"}

    try:
        response = requests.get(url, params=params)
        print(f"🔁 Status HTTP: {response.status_code}")
        if response.status_code != 200:
            return []

        items = response.json().get("collection", {}).get("items", [])[:max_results]
        results = []
        for item in items:
            data_block = item["data"][0]
            results.append({
                "title": data_block.get("title", "Sem título"),
                "description": data_block.get("description", "Sem descrição"),
                "date_created": data_block.get("date_created", "Desconhecida"),
                "image_url": item.get("links", [{}])[0].get("href", "")
            })
        return results

    except Exception as e:
        print(f"⚠️ Erro ao buscar imagens: {e}")
        return []

def download_and_show_image(image_url, filename):
    print(f"⬇️ Baixando imagem: {filename}")
    try:
        img = Image.open(BytesIO(requests.get(image_url).content))
        img.save(filename)
        print(f"💾 Imagem salva como: {filename}")
        img.show()
    except Exception as e:
        print(f"⚠️ Erro ao baixar/abrir imagem: {e}")

def main():
    print("🚀 Busca interativa por nebulosas (NASA + SIMBAD + VizieR + PyNeb)")
    query = escolher_nebulosa()
    dados = buscar_dados_simbad(query)
    imagens_baixadas = []

    if dados:
        print(f"\n📍 Coordenadas: RA = {dados['ra']}, DEC = {dados['dec']}")
        if dados['dist_ly']:
            print(f"🌌 Distância estimada: {dados['dist_ly']:.1f} anos-luz")
        else:
            print("🌌 Distância não disponível.")
    else:
        print("⚠️ Dados astronômicos não encontrados.")

    images = search_nasa_images(query, max_results=10)
    if not images:
        print("❌ Nenhuma imagem encontrada.")
        return

    print("\n✅ Resultados encontrados:")
    for idx, item in enumerate(images):
        print(f"\n[{idx+1}] {item['title']}")
        print(f"    📎 {item['image_url']}")
        print(f"    🗓️  Criada em: {item['date_created']}")
        print(f"    📄 {item['description'][:120]}...")

    selections = input("\nDigite os números das imagens para baixar (ex: 1 3 5): ")
    numeros_escolhidos = [int(n)-1 for n in selections.split() if n.isdigit()]

    for idx in numeros_escolhidos:
        if 0 <= idx < len(images):
            item = images[idx]
            data_formatada = item['date_created'].split("T")[0] if "T" in item['date_created'] else "data_desconhecida"
            nome_arquivo = f"{limpar_nome_arquivo(item['title'])}_{data_formatada}.jpg"
            download_and_show_image(item["image_url"], nome_arquivo)
            imagens_baixadas.append(nome_arquivo)
        else:
            print(f"⚠️ Índice inválido: {idx+1}")

    salvar_info_em_txt(query, dados, imagens_baixadas)

def mostrar_catalogo():
    print("\n📚 Catálogo de nebulosas:")
    for num, nome in CATALOGO_NEBULOSAS.items():
        print(f" {num}. {nome}")
    print(" 0. Buscar manualmente")

def escolher_nebulosa():
    mostrar_catalogo()
    escolha = input("\nDigite o número da nebulosa desejada ou 0 para buscar manualmente: ")

    if escolha.isdigit():
        escolha = int(escolha)
        if escolha == 0:
            return input("Digite o nome da nebulosa: ").strip()
        elif escolha in CATALOGO_NEBULOSAS:
            return CATALOGO_NEBULOSAS[escolha]
    print("❌ Opção inválida. Tente novamente.")
    return escolher_nebulosa()

if __name__ == "__main__":
    main()
