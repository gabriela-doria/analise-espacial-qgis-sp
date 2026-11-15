"""Redesenha os mapas finais a partir das camadas produzidas no QGIS.

Uso:  python scripts/desenhar_mapas.py camadas mapas pt
      python scripts/desenhar_mapas.py camadas mapas/en en

As camadas (GeoPackage, EPSG:31983) saíram do QGIS já com os campos calculados.
Este script não refaz a análise: só lê as camadas finais e desenha as figuras.
As quebras de classe são as mesmas usadas nos mapas entregues na disciplina.
"""
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D

CAMADAS = Path(sys.argv[1])
SAIDA = Path(sys.argv[2])
LANG = sys.argv[3] if len(sys.argv) > 3 else "pt"
SAIDA.mkdir(parents=True, exist_ok=True)

# ---------- estilo ----------
SURFACE, INK, INK2, INK3, RULE = "#FBFCFA", "#141D1A", "#3C4A45", "#6B7A74", "#C9D2C9"
PETROL = ["#E1EDED", "#B3D1D2", "#7BAEB1", "#3B8388", "#0E5259"]
AMBER = ["#F6EBD8", "#EBCF9E", "#D9AC5F", "#BF8528", "#8A5208"]
GRAY = ["#DCE0DB", "#BEC5BF", "#98A29B", "#6A756F", "#333F3A"]
EPSG = 31983

fams = {f.name for f in font_manager.fontManager.ttflist}
plt.rcParams["font.family"] = "Inter" if "Inter" in fams else "DejaVu Sans"
plt.rcParams["hatch.linewidth"] = 0.5
plt.rcParams["hatch.color"] = "#B9C2BA"

T = {
    "pt": dict(
        t15="A renda do distrito acompanha o acesso ao metrô?",
        s15="Município de São Paulo, por distrito. Mapa 1.5 do trabalho prático de SIG.",
        p15a="Moradores a até 800 m de uma estação",
        p15a_u="People Near Transit, % da população do distrito (Censo 2022)",
        p15b="Renda per capita",
        p15b_u="R$ por mês, Pesquisa Origem e Destino 2023",
        est="Estação de metrô",
        f15="Dados: Censo IBGE 2022 (setores censitários), Pesquisa OD 2023 (Metrô SP), estações (GeoSampa). "
            "Classes por quebras naturais (Jenks).",
        t25="Onde a cidade é mais construída tem metrô?",
        s25="Área construída por hexágono (IPTU 2022) e presença de estação, nas subprefeituras da Lapa e da "
            "Capela do Socorro.\nMesma escala e mesmas classes nos dois mapas. Mapa 2.5 do trabalho prático de SIG.",
        lapa="LAPA", cs="CAPELA DO SOCORRO",
        leg25="Área construída no hexágono (mil m²)",
        sem="sem estação", com="com estação", nd="Sem registro de IPTU no hexágono",
        f25="Dados: IPTU 2022, Painel Cadastral da Cidade de São Paulo (PMSP); estações e subprefeituras "
            "(GeoSampa). Grade hexagonal de 12 ha por célula.\nClasses por quebras naturais (Jenks), iguais "
            "nas duas áreas.",
        t12="Onde São Paulo é mais adensada?",
        s12="Densidade demográfica por distrito. Mapa 1.2 do trabalho prático de SIG.",
        p12_u="Habitantes por hectare, Pesquisa Origem e Destino 2023",
        f12="Dados: Pesquisa OD 2023 (Metrô SP), agregada de zona OD para distrito. Classes por quebras "
            "naturais (Jenks).",
        cred="SRC: SIRGAS 2000 / UTM 23S (EPSG:31983). Análise no QGIS: Gabriela Dória, PTR3312, Poli-USP, 2026. "
             "Figura redesenhada em Python a partir das camadas finais.",
        dec=",", mil=".", a=" a ",
    ),
    "en": dict(
        t15="Does district income follow access to the metro?",
        s15="City of São Paulo, by district. Map 1.5 of the GIS course project.",
        p15a="Residents within 800 m of a station",
        p15a_u="People Near Transit, % of district population (2022 Census)",
        p15b="Per capita income",
        p15b_u="BRL per month, 2023 Origin-Destination Survey",
        est="Metro station",
        f15="Data: IBGE 2022 Census (census tracts), 2023 OD Survey (Metrô SP), stations (GeoSampa). "
            "Classes by natural breaks (Jenks).",
        t25="Is the metro where the city is most built up?",
        s25="Built area per hexagon (2022 property-tax records) and station presence, in the Lapa and "
            "Capela do Socorro boroughs.\nSame scale and same classes on both maps. Map 2.5 of the GIS course project.",
        lapa="LAPA", cs="CAPELA DO SOCORRO",
        leg25="Built area in the hexagon (thousand m²)",
        sem="no station", com="with station", nd="No property-tax record in the hexagon",
        f25="Data: 2022 IPTU property-tax records, São Paulo cadastral panel (PMSP); stations and boroughs "
            "(GeoSampa). Hexagonal grid, 12 ha per cell.\nClasses by natural breaks (Jenks), identical "
            "in both areas.",
        t12="Where is São Paulo densest?",
        s12="Population density by district. Map 1.2 of the GIS course project.",
        p12_u="Inhabitants per hectare, 2023 Origin-Destination Survey",
        f12="Data: 2023 OD Survey (Metrô SP), aggregated from OD zone to district. Classes by natural "
            "breaks (Jenks).",
        cred="CRS: SIRGAS 2000 / UTM 23S (EPSG:31983). Analysis in QGIS: Gabriela Dória, PTR3312, Poli-USP, 2026. "
             "Figure redrawn in Python from the final layers.",
        dec=".", mil=",", a=" to ",
    ),
}[LANG]


def num(v, casas=0):
    s = f"{v:,.{casas}f}"
    return s.replace(",", "§").replace(".", T["dec"]).replace("§", T["mil"])


def ler(nome):
    g = gpd.read_file(CAMADAS / nome)
    return g.set_crs(EPSG) if g.crs is None else g


def classe(v, quebras):
    for i, q in enumerate(quebras):
        if v <= q:
            return i
    return len(quebras)


def enquadrar(ax, fig, cx, cy, escala):
    """Fixa a janela do eixo para que 1 m valha `escala` polegadas."""
    box = ax.get_position()
    w, h = box.width * fig.get_figwidth(), box.height * fig.get_figheight()
    ax.set_xlim(cx - w / (2 * escala), cx + w / (2 * escala))
    ax.set_ylim(cy - h / (2 * escala), cy + h / (2 * escala))
    ax.set_aspect("equal")
    ax.axis("off")


def barra_escala(ax, x0, y0, km, partes=2):
    passo = km * 1000 / partes
    alt = (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.006
    for i in range(partes):
        ax.add_patch(Rectangle((x0 + i * passo, y0), passo, alt, fc=INK if i % 2 == 0 else SURFACE,
                               ec=INK, lw=0.6, zorder=6))
    for i in range(partes + 1):
        rot = num(km * i / partes, 0 if (km * i / partes) % 1 == 0 else 1)
        ax.text(x0 + i * passo, y0 + alt * 2.2, rot, ha="center", va="bottom", fontsize=8.5, color=INK2, zorder=6)
    ax.text(x0 + partes * passo + passo * 0.12, y0 + alt * 0.5, "km", ha="left", va="center", fontsize=8.5,
            color=INK2, zorder=6)


def norte(ax, x, y, tam):
    ax.annotate("", xy=(x, y + tam), xytext=(x, y), zorder=6,
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.1, mutation_scale=11))
    ax.text(x, y + tam * 1.12, "N", ha="center", va="bottom", fontsize=9.5, fontweight="bold", color=INK)


def legenda_classes(fig, x, y, titulo, unidade, cores, limites, casas=0, extra=None):
    """Legenda em blocos empilhados, em coordenadas da figura (0 a 1)."""
    fig.text(x, y, titulo, fontsize=12.5, fontweight="bold", color=INK, va="bottom")
    fig.text(x, y - 0.022, unidade, fontsize=9, color=INK3, va="bottom")
    ax = fig.add_axes([x, y - 0.045 - 0.031 * (len(cores) + (1 if extra else 0)), 0.2,
                       0.031 * (len(cores) + (1 if extra else 0))])
    ax.axis("off"); ax.set_xlim(0, 10); n = len(cores) + (1 if extra else 0); ax.set_ylim(0, n)
    for i, c in enumerate(cores):
        yy = n - 1 - i
        ax.add_patch(Rectangle((0, yy + 0.12), 0.95, 0.76, fc=c, ec=RULE, lw=0.5))
        ax.text(1.3, yy + 0.5, f"{num(limites[i], casas)}{T['a']}{num(limites[i + 1], casas)}",
                va="center", fontsize=10, color=INK2)
    if extra:
        ax.scatter([0.47], [0.5], s=16, fc=SURFACE, ec=INK, lw=0.8)
        ax.text(1.3, 0.5, extra, va="center", fontsize=10, color=INK2)


def cabecalho(fig, titulo, sub, x=0.035, y=0.945):
    fig.text(x, y, titulo, fontsize=23, fontweight="bold", color=INK, va="bottom")
    fig.text(x, y - 0.012, sub, fontsize=11.5, color=INK2, va="top", linespacing=1.45)


def rodape(fig, fonte, x=0.035, y=0.028, estreito=False):
    cred = T["cred"].replace(", 2026. ", ", 2026.\n") if estreito else T["cred"]
    fig.text(x, y, fonte + "\n" + cred, fontsize=8.3, color=INK3, va="bottom", linespacing=1.5)


def distritos_sp(nome):
    return ler(nome)


def coropletico(ax, g, campo, quebras, cores):
    g = g.assign(_c=g[campo].apply(lambda v: classe(v, quebras[1:-1])))
    for i, c in enumerate(cores):
        sel = g[g._c == i]
        if len(sel):
            sel.plot(ax=ax, color=c, edgecolor=SURFACE, linewidth=0.55)
    g.dissolve().boundary.plot(ax=ax, color=INK2, linewidth=0.7)


# ---------- Mapa 1.5 ----------
def mapa_15():
    d = distritos_sp("distritos_renda_e_acesso_ao_metro.gpkg")
    est = ler("estacoes_metro.gpkg")
    fig = plt.figure(figsize=(15, 10.4), facecolor=SURFACE)
    cabecalho(fig, T["t15"], T["s15"])
    xmin, ymin, xmax, ymax = d.total_bounds
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    a1 = fig.add_axes([0.02, 0.085, 0.47, 0.80]); a2 = fig.add_axes([0.51, 0.085, 0.47, 0.80])
    esc = (0.80 * 10.4) / ((ymax - ymin) * 1.04)
    q_pnt = [0, 6.4, 20.1, 41.9, 60.9, 100]          # quebras do mapa entregue
    q_renda = [1151, 2143, 3230, 4464, 6503, 10093]  # quebras do mapa entregue
    for ax, campo, q, cores in [(a1, "perc_ate_800m_metro", q_pnt, PETROL), (a2, "renda_per_capita_od2023", q_renda, AMBER)]:
        enquadrar(ax, fig, cx - 6500, cy, esc)
        coropletico(ax, d, campo, q, cores)
    est.plot(ax=a1, markersize=7, facecolor=SURFACE, edgecolor=INK, linewidth=0.55, zorder=5)
    legenda_classes(fig, 0.315, 0.40, T["p15a"], T["p15a_u"], PETROL, q_pnt, casas=1, extra=T["est"])
    legenda_classes(fig, 0.805, 0.40, T["p15b"], T["p15b_u"], AMBER, q_renda)
    barra_escala(a1, xmin - 9000, ymin + 2500, 20)
    norte(a1, xmin - 6000, ymax - 9000, 5000)
    rodape(fig, T["f15"])
    fig.savefig(SAIDA / f"mapa-1-5-renda-e-acesso-ao-metro-{LANG}.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


# ---------- Mapa 1.2 ----------
def mapa_12():
    d = distritos_sp("distritos_densidade_demografica.gpkg")
    fig = plt.figure(figsize=(9.6, 10.4), facecolor=SURFACE)
    cabecalho(fig, T["t12"], T["s12"], x=0.055)
    xmin, ymin, xmax, ymax = d.total_bounds
    ax = fig.add_axes([0.02, 0.085, 0.96, 0.80])
    esc = (0.80 * 10.4) / ((ymax - ymin) * 1.04)
    enquadrar(ax, fig, (xmin + xmax) / 2 + 9000, (ymin + ymax) / 2, esc)
    q = [2, 44, 96, 134, 182, 280]                   # quebras do mapa entregue
    coropletico(ax, d, "densidade_hab_ha_od2023", q, PETROL)
    legenda_classes(fig, 0.62, 0.40, "Densidade demográfica" if LANG == "pt" else "Population density",
                    T["p12_u"], PETROL, q)
    barra_escala(ax, xmin - 9000, ymin + 2500, 20)
    norte(ax, xmin - 6000, ymax - 9000, 5000)
    rodape(fig, T["f12"], x=0.055, y=0.02, estreito=True)
    fig.savefig(SAIDA / f"mapa-1-2-densidade-demografica-{LANG}.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


# ---------- Mapa 2.5 ----------
def mapa_25():
    campo = "area_construida_m2_iptu2022"
    q = [73308, 164950, 277038, 412066]              # regras do projeto QGIS
    lapa, cs = ler("hexagonos_lapa.gpkg"), ler("hexagonos_capela_do_socorro.gpkg")
    sl, sc = ler("subprefeitura_lapa.gpkg"), ler("subprefeitura_capela_do_socorro.gpkg")
    est = ler("estacoes_metro.gpkg")
    fig = plt.figure(figsize=(15, 11.6), facecolor=SURFACE)
    cabecalho(fig, T["t25"], T["s25"], y=0.95)
    a1 = fig.add_axes([0.02, 0.40, 0.50, 0.42]); a2 = fig.add_axes([0.60, 0.075, 0.385, 0.80])
    bl, bc = sl.total_bounds, sc.total_bounds
    esc = (0.80 * 11.6) / ((bc[3] - bc[1]) * 1.05)
    enquadrar(a1, fig, (bl[0] + bl[2]) / 2, (bl[1] + bl[3]) / 2, esc)
    enquadrar(a2, fig, (bc[0] + bc[2]) / 2, (bc[1] + bc[3]) / 2, esc)
    for ax, hexs, sub, nome in [(a1, lapa, sl, T["lapa"]), (a2, cs, sc, T["cs"])]:
        vazio = hexs[hexs[campo].isna()]
        if len(vazio):
            vazio.plot(ax=ax, facecolor=SURFACE, edgecolor="#E3E7E2", linewidth=0.3, hatch="////")
        dados = hexs[hexs[campo].notna()].copy()
        dados["_c"] = dados[campo].apply(lambda v: classe(v, q))
        dados["_m"] = dados["n_estacoes"].fillna(0) > 0
        for metro, rampa in [(False, GRAY), (True, AMBER)]:
            for i, c in enumerate(rampa):
                sel = dados[(dados._c == i) & (dados._m == metro)]
                if len(sel):
                    sel.plot(ax=ax, color=c, edgecolor=SURFACE, linewidth=0.5,
                             zorder=3 if metro else 2)
        com = dados[dados._m]
        if len(com):
            com.boundary.plot(ax=ax, color=AMBER[4], linewidth=1.3, zorder=4)
        sub.boundary.plot(ax=ax, color=INK, linewidth=1.0, zorder=4)
        perto = est[est.within(sub.buffer(600).union_all())]
        perto.plot(ax=ax, markersize=20, facecolor=SURFACE, edgecolor=INK, linewidth=0.9, zorder=5)
        b = sub.total_bounds
        ax.text(b[0], b[3] + 350, nome, fontsize=12, fontweight="bold", color=INK, va="bottom")
    barra_escala(a1, bl[0], bl[1] - 1150, 4)
    norte(a1, bl[2] + 600, bl[3] - 300, 900)
    # legenda bivariada: 2 linhas (sem/com estação) x 5 classes
    lx, ly = 0.035, 0.305
    fig.text(lx, ly, T["leg25"], fontsize=12.5, fontweight="bold", color=INK, va="bottom")
    lg = fig.add_axes([lx, ly - 0.145, 0.46, 0.135]); lg.axis("off"); lg.set_xlim(0, 23); lg.set_ylim(0, 4.4)
    lim = [0] + [v / 1000 for v in q]
    for j, (rampa, rot) in enumerate([(GRAY, T["sem"]), (AMBER, T["com"])]):
        yy = 2.9 - j * 1.05
        lg.text(0, yy + 0.45, rot, va="center", fontsize=10, color=INK2)
        for i, c in enumerate(rampa):
            lg.add_patch(Rectangle((5.2 + i * 3.4, yy), 3.3, 0.9, fc=c, ec=RULE, lw=0.5))
    for i in range(5):
        rot = f"{num(lim[i])}{T['a']}{num(lim[i + 1])}" if i < 4 else ("> " + num(lim[4]))
        lg.text(5.2 + i * 3.4 + 1.65, 1.6, rot, ha="center", va="top", fontsize=9.3, color=INK2)
    lg.add_patch(Rectangle((0, 0.05), 1.5, 0.75, fc=SURFACE, ec="#D5DBD4", lw=0.5, hatch="////"))
    lg.text(1.9, 0.42, T["nd"], va="center", fontsize=10, color=INK2)
    lg.scatter([11.6], [0.42], s=22, fc=SURFACE, ec=INK, lw=0.9)
    lg.text(12.1, 0.42, T["est"], va="center", fontsize=10, color=INK2)
    rodape(fig, T["f25"])
    fig.savefig(SAIDA / f"mapa-2-5-area-construida-e-metro-{LANG}.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    mapa_15(); mapa_12(); mapa_25()
    print("ok:", sorted(p.name for p in SAIDA.glob(f"*-{LANG}.png")))
