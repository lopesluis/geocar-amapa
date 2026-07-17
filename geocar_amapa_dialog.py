# -*- coding: utf-8 -*-
"""
GeoCAR Amapá - Lógica principal da interface e processamento
"""

import os
import re
import hashlib
import shutil
import time
from datetime import datetime

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QFileDialog, QTextEdit, QGroupBox, QGridLayout, QFrame,
    QScrollArea, QProgressBar, QMessageBox, QProgressDialog, QApplication
)
from qgis.PyQt.QtCore import Qt, QUrl, QEventLoop
from qgis.PyQt.QtGui import QFont, QIcon

from qgis.core import (
    QgsProject, QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsVectorFileWriter, QgsFeature, QgsGeometry,
    QgsWkbTypes, QgsField, QgsFields, QgsApplication, QgsFileDownloader,
)
from qgis.PyQt.QtCore import QVariant

import processing


# ─────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────

MUNICIPIOS_AP = [
    "Amapá", "Calçoene", "Cutias", "Ferreira Gomes",
    "Itaubal", "Laranjal do Jari", "Macapá", "Mazagão",
    "Oiapoque", "Pedra Branca do Amapari", "Porto Grande",
    "Pracuúba", "Santana", "Serra do Navio",
    "Tartarugalzinho", "Vitória do Jari"
]

CAMADAS_BASE = {
    "area_antropizada":        {"nome": "Área Antropizada",                       "clip": True,  "buffer": False, "virtual": False},
    "area_consolidada":        {"nome": "Área Consolidada",                        "clip": True,  "buffer": False, "virtual": False},
    "servidao_administrativa": {"nome": "Servidão Administrativa",                 "clip": True,  "buffer": False, "virtual": False},
    "vegetacao":               {"nome": "Remanescente de Vegetação Nativa (RVN)",  "clip": True,  "buffer": False, "virtual": False},
    "hidrografia":             {"nome": "Hidrografia",                             "clip": True,  "buffer": True,  "virtual": False},
    "cerrado":                 {"nome": "Cerrado",                                 "clip": False, "buffer": False, "virtual": True},
    "floresta":                {"nome": "Floresta",                                "clip": False, "buffer": False, "virtual": True},
    "campo":                   {"nome": "Campo",                                   "clip": False, "buffer": False, "virtual": True},
}

FATORES_RL = {
    "cerrado":  0.35,
    "floresta": 0.80,
    "campo":    0.20,
}

BASE_URL = (
    "https://github.com/lopesluis/geocar-amapa/releases/download/"
    "v1.0/base_ambiental_ap.gpkg"
)
BASE_SHA256 = "".join((
    "78f470878e855a62",
    "a5574a92f151b30f",
    "caa0b37867c88c1f",
    "580c40d186f07ec6",
))
BASE_ARQUIVO = "base_ambiental_ap.gpkg"
BASE_VERSAO = "v1.0"

# Categorias conhecidas da hidrografia — usado para slug do nome de arquivo
HIDRO_SLUG = {
    "Acima de 600m":              "acima_600m",
    "Ate 10m":                    "ate_10m",
    "Entre 10m e 50m":            "entre_10_50m",
    "Entre 200m e 600m":          "entre_200_600m",
    "Entre 50m e 200m":           "entre_50_200m",
    "Lago ou Lagoa Natural":      "lago_lagoa",
    "Reservatorio Artificial":    "reservatorio_artificial",
    "ReservatÃ³rio Artificial":   "reservatorio_artificial",
}

ESTILO = """
/* Visual deliberadamente discreto: preserva o tema nativo do QGIS/Qt. */
QDialog {
    background-color: palette(window);
}
QTabWidget::pane {
    border: 1px solid palette(mid);
    top: -1px;
}
QTabBar::tab {
    padding: 7px 14px;
    margin-right: 2px;
}
QGroupBox {
    font-weight: 600;
    margin-top: 10px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
}
QLineEdit, QComboBox {
    min-height: 24px;
}
QPushButton {
    min-height: 26px;
    padding: 3px 10px;
}
QPushButton#btn_processar, QPushButton#btn_carregar {
    min-height: 32px;
    padding: 5px 16px;
    font-weight: 600;
}
QTextEdit {
    font-family: monospace;
}
QProgressBar {
    min-height: 20px;
    text-align: center;
}
QScrollArea {
    border: none;
    background: transparent;
}
"""


# ─────────────────────────────────────────────
# Widget status de camada
# ─────────────────────────────────────────────

class CamadaStatusWidget(QFrame):
    def __init__(self, nome, disponivel, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)
        icone = QLabel("✓" if disponivel else "!")
        icone.setFixedWidth(16)
        layout.addWidget(icone)
        lbl = QLabel(nome)
        layout.addWidget(lbl)
        layout.addStretch()
        status = QLabel("Disponível" if disponivel else "Não encontrada")
        status.setEnabled(disponivel)
        layout.addWidget(status)


# ─────────────────────────────────────────────
# Cabeçalho
# ─────────────────────────────────────────────

class CabecalhoWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cabecalhoGeoCAR")
        self.setStyleSheet("""
            QFrame#cabecalhoGeoCAR {
                background-color: #315C45;
                border-radius: 4px;
            }
            QFrame#cabecalhoGeoCAR QLabel {
                color: white;
                background: transparent;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 11, 16, 11)
        layout.setSpacing(10)

        txt_layout = QVBoxLayout()
        txt_layout.setSpacing(2)
        titulo = QLabel("GeoCAR Amapá")
        titulo.setFont(QFont("Segoe UI", 15, QFont.Bold))
        txt_layout.addWidget(titulo)
        subtitulo = QLabel("Base de Referência e apoio ao Cadastro Ambiental Rural no Amapá")
        subtitulo.setStyleSheet("color: #DCE8E1;")
        txt_layout.addWidget(subtitulo)
        layout.addLayout(txt_layout)
        layout.addStretch()

        versao = QLabel("v1.2")
        versao.setStyleSheet("color: #DCE8E1; padding: 2px 4px;")
        layout.addWidget(versao)



# ─────────────────────────────────────────────
# Diálogo principal
# ─────────────────────────────────────────────

class GeoCARAmapaDiag(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # A base é armazenada fora da pasta do plugin para permanecer disponível
        # após atualizações ou reinstalações do complemento.
        self.base_dir = os.path.join(
            QgsApplication.qgisSettingsDirPath(),
            "geocar_amapa",
            "camadas_base"
        )
        self.gpkg_path_persistente = os.path.join(self.base_dir, BASE_ARQUIVO)
        self.gpkg_path_legado = os.path.join(
            self.plugin_dir, "camadas_base", BASE_ARQUIVO
        )
        self.gpkg_path = self._resolver_caminho_base()

        self.pasta_saida = ""
        self.log_msgs = []

        self.setWindowTitle("GeoCAR Amapá")
        self.setMinimumSize(720, 700)
        self.setStyleSheet(ESTILO)
        self._build_ui()
        self._atualizar_camadas()
        self._verificar_gpkg()
        self._oferecer_download_base()

    # ── UI ───────────────────────────────────

    def _build_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setSpacing(12)
        layout_principal.setContentsMargins(12, 12, 12, 12)
        layout_principal.addWidget(CabecalhoWidget())

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._aba_processar(), "Processar CAR")
        self.tabs.addTab(self._aba_base(), "Base de Referência")
        self.tabs.addTab(self._aba_log(), "Log de Processamento")
        layout_principal.addWidget(self.tabs)

    def _aba_processar(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Identificação
        grp_id = QGroupBox("Identificação do Posseiro / Imóvel")
        grid = QGridLayout(grp_id)
        grid.setSpacing(8)
        grid.addWidget(QLabel("Nome do Posseiro / Proprietário: *"), 0, 0)
        self.txt_nome = QLineEdit()
        self.txt_nome.setPlaceholderText("Ex: João da Silva Pereira")
        grid.addWidget(self.txt_nome, 0, 1)
        grid.addWidget(QLabel("CPF: *"), 1, 0)
        self.txt_cpf = QLineEdit()
        self.txt_cpf.setPlaceholderText("000.000.000-00")
        self.txt_cpf.setInputMask("000.000.000-00")
        grid.addWidget(self.txt_cpf, 1, 1)
        grid.addWidget(QLabel("Nome da Posse / Imóvel: *"), 2, 0)
        self.txt_posse = QLineEdit()
        self.txt_posse.setPlaceholderText("Ex: Sítio Boa Esperança")
        grid.addWidget(self.txt_posse, 2, 1)
        grid.addWidget(QLabel("Estado:"), 3, 0)
        txt_estado = QLineEdit("Amapá — AP")
        txt_estado.setDisabled(True)
        grid.addWidget(txt_estado, 3, 1)
        grid.addWidget(QLabel("Município: *"), 4, 0)
        self.cmb_municipio = QComboBox()
        self.cmb_municipio.addItems(MUNICIPIOS_AP)
        grid.addWidget(self.cmb_municipio, 4, 1)
        layout.addWidget(grp_id)

        # Camada do imóvel
        grp_imovel = QGroupBox("Polígono do Imóvel")
        imovel_layout = QGridLayout(grp_imovel)
        imovel_layout.addWidget(QLabel("Camada do imóvel (polígono): *"), 0, 0)
        h = QHBoxLayout()
        self.cmb_camada = QComboBox()
        h.addWidget(self.cmb_camada)
        btn_refresh = QPushButton("Atualizar")
        btn_refresh.setObjectName("btn_secundario")
        btn_refresh.setFixedWidth(72)
        btn_refresh.setToolTip("Atualizar lista de camadas")
        btn_refresh.clicked.connect(self._atualizar_camadas)
        h.addWidget(btn_refresh)
        imovel_layout.addLayout(h, 0, 1)
        layout.addWidget(grp_imovel)

        # Fitofisionomia
        grp_fito = QGroupBox("Fitofisionomia — Estimativa de Reserva Legal")
        fito_layout = QVBoxLayout(grp_fito)
        info_lbl = QLabel(
            "Marque as fitofisionomias presentes no imóvel. O plugin calculará virtualmente "
            "a área de cada uma dentro do polígono e estimará o tamanho mínimo da Reserva Legal "
            "conforme o Código Florestal (Lei 12.651/2012)."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("padding: 2px 0;")
        fito_layout.addWidget(info_lbl)
        self.chk_cerrado  = QCheckBox("Cerrado  (RL = 35% da área de Cerrado)")
        self.chk_floresta = QCheckBox("Floresta  (RL = 80% da área de Floresta)")
        self.chk_campo    = QCheckBox("Campo  (RL = 20% da área de Campo)")
        for chk in [self.chk_cerrado, self.chk_floresta, self.chk_campo]:
            chk.setFont(QFont("Segoe UI", 11))
            fito_layout.addWidget(chk)
        layout.addWidget(grp_fito)

        # Pasta de saída
        grp_pasta = QGroupBox("Pasta de Saída")
        pasta_layout = QHBoxLayout(grp_pasta)
        self.txt_pasta = QLineEdit()
        self.txt_pasta.setPlaceholderText("Selecione a pasta onde os resultados serão salvos...")
        self.txt_pasta.setReadOnly(True)
        pasta_layout.addWidget(self.txt_pasta)
        btn_pasta = QPushButton("Selecionar Pasta")
        btn_pasta.setObjectName("btn_secundario")
        btn_pasta.clicked.connect(self._selecionar_pasta)
        pasta_layout.addWidget(btn_pasta)
        layout.addWidget(grp_pasta)

        # Status camadas base
        grp_status = QGroupBox("Camadas Base — Status")
        self.status_layout = QVBoxLayout(grp_status)
        self.status_layout.setSpacing(4)
        layout.addWidget(grp_status)

        # Progresso
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Botão processar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_processar = QPushButton("Processar CAR")
        self.btn_processar.setObjectName("btn_processar")
        self.btn_processar.setMinimumWidth(220)
        self.btn_processar.clicked.connect(self._processar)
        btn_layout.addWidget(self.btn_processar)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        layout.addStretch()

        scroll.setWidget(inner)
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return widget

    def _aba_base(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        info = QLabel(
            "Esta função carrega todas as camadas de referência do estado do Amapá "
            "diretamente no projeto QGIS, organizadas no grupo "
            "<b>Base de Referência CAR — Amapá</b>.<br><br>"
            "Use esta opção para visualizar, consultar e analisar as camadas sem executar "
            "recortes ou cálculos."
        )
        info.setWordWrap(True)
        try:
            info.setTextFormat(Qt.TextFormat.RichText)
        except AttributeError:
            info.setTextFormat(Qt.RichText)
        layout.addWidget(info)

        self.lbl_status_base = QLabel()
        self.lbl_status_base.setWordWrap(True)
        layout.addWidget(self.lbl_status_base)

        acoes_base = QHBoxLayout()
        self.btn_baixar_base = QPushButton("Baixar Base de Referência")
        self.btn_baixar_base.clicked.connect(self._baixar_base_referencia)
        acoes_base.addWidget(self.btn_baixar_base)

        self.btn_abrir_pasta_base = QPushButton("Abrir pasta da base")
        self.btn_abrir_pasta_base.clicked.connect(self._abrir_pasta_base)
        acoes_base.addWidget(self.btn_abrir_pasta_base)
        acoes_base.addStretch()
        layout.addLayout(acoes_base)

        grp = QGroupBox("Camadas que serão carregadas")
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(4)
        camadas_info = [
            "Área Antropizada",
            "Área Consolidada",
            "Servidão Administrativa",
            "Remanescente de Vegetação Nativa (RVN)",
            "Hidrografia",
            "Cerrado",
            "Floresta",
            "Campo",
        ]
        for nome in camadas_info:
            row = QFrame()
            row.setFrameShape(QFrame.StyledPanel)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 5, 8, 5)
            lbl_n = QLabel(nome)
            row_layout.addWidget(lbl_n)
            row_layout.addStretch()
            grp_layout.addWidget(row)
        layout.addWidget(grp)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_carregar = QPushButton("Carregar Base de Referência no QGIS")
        btn_carregar.setObjectName("btn_carregar")
        btn_carregar.setMinimumWidth(280)
        btn_carregar.clicked.connect(self._carregar_base_referencia)
        btn_layout.addWidget(btn_carregar)
        layout.addLayout(btn_layout)
        return widget

    def _aba_log(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        info = QLabel(
            "Acompanhe abaixo as mensagens geradas durante o processamento. "
            "O conteúdo é atualizado em tempo real."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setPlaceholderText("As mensagens de processamento aparecerão aqui...")
        layout.addWidget(self.txt_log, 1)

        botoes = QHBoxLayout()
        botoes.addStretch()
        btn_limpar_log = QPushButton("Limpar log")
        btn_limpar_log.clicked.connect(self._limpar_log)
        botoes.addWidget(btn_limpar_log)
        layout.addLayout(botoes)
        return widget

    def _limpar_log(self):
        self.txt_log.clear()
        self.log_msgs = []

    # ── Auxiliares ───────────────────────────

    def _log(self, msg, tipo="info"):
        hora = datetime.now().strftime("%H:%M:%S")
        icones = {"info": "ℹ️", "ok": "✅", "erro": "❌", "aviso": "⚠️"}
        self.txt_log.append(f"[{hora}] {icones.get(tipo,'ℹ️')}  {msg}")
        self.log_msgs.append(f"[{hora}] [{tipo.upper()}] {msg}")

    def _atualizar_camadas(self):
        self.cmb_camada.clear()
        self.cmb_camada.addItem("— Selecione a camada do imóvel —", None)
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.cmb_camada.addItem(layer.name(), layer.id())

    def _resolver_caminho_base(self):
        """Retorna o caminho da base, priorizando a pasta persistente."""
        if os.path.exists(self.gpkg_path_persistente):
            return self.gpkg_path_persistente
        if os.path.exists(self.gpkg_path_legado):
            return self.gpkg_path_legado
        return self.gpkg_path_persistente

    def _oferecer_download_base(self):
        """Oferece o download apenas quando nenhuma base estiver disponível."""
        if os.path.exists(self.gpkg_path):
            return

        resposta = QMessageBox.question(
            self,
            "Base de Referência não instalada",
            "O GeoCAR Amapá necessita da Base de Referência para realizar "
            "consultas, recortes e cálculos orientativos.\n\n"
            "O arquivo possui aproximadamente 602 MB e será salvo "
            "automaticamente no perfil do QGIS.\n\n"
            "Deseja baixar a Base de Referência agora?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if resposta == QMessageBox.Yes:
            self._baixar_base_referencia()

    def _calcular_sha256(self, caminho):
        sha = hashlib.sha256()
        with open(caminho, "rb") as arquivo:
            for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
                sha.update(bloco)
        return sha.hexdigest()

    def _baixar_base_referencia(self):
        """Baixa, valida e instala automaticamente a Base de Referência."""
        os.makedirs(self.base_dir, exist_ok=True)
        arquivo_temporario = self.gpkg_path_persistente + ".part"

        # Remove eventual arquivo temporário deixado por tentativa anterior.
        if os.path.exists(arquivo_temporario):
            try:
                os.remove(arquivo_temporario)
            except OSError as erro:
                QMessageBox.warning(
                    self,
                    "Arquivo temporário em uso",
                    "Não foi possível remover um download temporário anterior. "
                    "Feche outras instâncias do QGIS e tente novamente.\n\n"
                    f"Detalhes: {erro}"
                )
                return

        progresso = QProgressDialog(
            "Preparando o download da Base de Referência...",
            "Cancelar",
            0,
            100,
            self
        )
        progresso.setWindowTitle("GeoCAR Amapá")
        progresso.setWindowModality(Qt.WindowModal)
        progresso.setMinimumDuration(0)
        progresso.setValue(0)

        estado = {
            "concluido": False,
            "cancelado": False,
            "erro": None,
        }

        loop = QEventLoop()

        # QgsFileDownloader usa a infraestrutura de rede nativa do QGIS.
        # delayStart=True permite conectar todos os sinais antes do início.
        downloader = QgsFileDownloader(
            QUrl(BASE_URL),
            arquivo_temporario,
            "",
            True
        )

        def ao_progredir(bytes_recebidos, bytes_total):
            if bytes_total > 0:
                percentual = min(99, int(bytes_recebidos * 100 / bytes_total))
                progresso.setValue(percentual)
                progresso.setLabelText(
                    "Baixando Base de Referência...\n"
                    f"{bytes_recebidos / (1024 * 1024):.1f} MB de "
                    f"{bytes_total / (1024 * 1024):.1f} MB"
                )
            else:
                progresso.setLabelText(
                    "Baixando Base de Referência...\n"
                    f"{bytes_recebidos / (1024 * 1024):.1f} MB recebidos"
                )
            QApplication.processEvents()

        def ao_concluir(_url):
            estado["concluido"] = True

        def ao_falhar(mensagens):
            estado["erro"] = "\n".join(str(msg) for msg in mensagens)

        def ao_cancelar():
            estado["cancelado"] = True

        downloader.downloadProgress.connect(ao_progredir)
        downloader.downloadCompleted.connect(ao_concluir)
        downloader.downloadError.connect(ao_falhar)
        downloader.downloadCanceled.connect(ao_cancelar)
        downloader.downloadExited.connect(loop.quit)
        progresso.canceled.connect(downloader.cancelDownload)

        try:
            downloader.startDownload()
            loop.exec()

            if estado["cancelado"]:
                raise InterruptedError("Download cancelado pelo usuário.")

            if estado["erro"]:
                raise RuntimeError(estado["erro"])

            if not estado["concluido"] or not os.path.exists(arquivo_temporario):
                raise RuntimeError(
                    "O download foi encerrado sem gerar um arquivo válido."
                )

            progresso.setLabelText("Verificando a integridade do arquivo...")
            progresso.setValue(99)
            QApplication.processEvents()

            hash_obtido = self._calcular_sha256(arquivo_temporario)
            if hash_obtido.lower() != BASE_SHA256.lower():
                raise ValueError(
                    "A verificação SHA-256 falhou. O arquivo baixado pode estar "
                    "incompleto ou alterado."
                )

            # No Windows, antivírus/indexadores podem manter o .part bloqueado
            # por alguns instantes. Tenta a troca atômica algumas vezes.
            instalado = False
            ultimo_erro = None
            for _ in range(5):
                try:
                    os.replace(arquivo_temporario, self.gpkg_path_persistente)
                    instalado = True
                    break
                except PermissionError as erro:
                    ultimo_erro = erro
                    time.sleep(0.5)

            # Fallback: copia o arquivo validado para o destino definitivo.
            if not instalado:
                try:
                    shutil.copy2(arquivo_temporario, self.gpkg_path_persistente)
                    instalado = True
                except OSError as erro:
                    ultimo_erro = erro

            if not instalado:
                raise RuntimeError(
                    "Não foi possível finalizar a instalação da Base de Referência. "
                    f"Detalhes: {ultimo_erro}"
                )

            # Tenta limpar o .part, sem falhar caso o Windows ainda o mantenha bloqueado.
            if os.path.exists(arquivo_temporario):
                try:
                    os.remove(arquivo_temporario)
                except OSError:
                    pass

            self.gpkg_path = self.gpkg_path_persistente
            progresso.setValue(100)

            self._log(
                f"Base de Referência {BASE_VERSAO} instalada com sucesso.",
                "ok"
            )
            self._verificar_gpkg()

            QMessageBox.information(
                self,
                "Base instalada",
                "A Base de Referência foi baixada, validada e instalada com "
                "sucesso. O GeoCAR Amapá já está pronto para uso."
            )

        except InterruptedError:
            if os.path.exists(arquivo_temporario):
                try:
                    os.remove(arquivo_temporario)
                except OSError:
                    pass
            self._log("Download da Base de Referência cancelado.", "aviso")

        except Exception as erro:
            if os.path.exists(arquivo_temporario):
                try:
                    os.remove(arquivo_temporario)
                except OSError:
                    pass
            self._log(f"Erro ao instalar a Base de Referência: {erro}", "erro")
            QMessageBox.critical(
                self,
                "Erro na instalação da base",
                "A Base de Referência não pôde ser instalada.\n\n"
                f"Detalhes: {erro}"
            )

        finally:
            progresso.close()

    def _abrir_pasta_base(self):
        """Abre a pasta persistente da base no gerenciador de arquivos."""
        os.makedirs(self.base_dir, exist_ok=True)
        try:
            from qgis.PyQt.QtCore import QUrl
            from qgis.PyQt.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.base_dir))
        except Exception as erro:
            QMessageBox.warning(
                self,
                "Não foi possível abrir a pasta",
                f"A pasta da base está localizada em:\n{self.base_dir}\n\n"
                f"Detalhes: {erro}"
            )

    def _verificar_gpkg(self):
        while self.status_layout.count():
            item = self.status_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not os.path.exists(self.gpkg_path):
            if hasattr(self, "lbl_status_base"):
                self.lbl_status_base.setText(
                    "⚠️ Base de Referência não instalada. Clique em "
                    "<b>Baixar Base de Referência</b>."
                )
                self.btn_baixar_base.setText("Baixar Base de Referência")
                self.btn_abrir_pasta_base.setEnabled(False)
            self.status_layout.addWidget(
                CamadaStatusWidget(
                    "Arquivo base_ambiental_ap.gpkg não encontrado!",
                    False
                )
            )
            return

        if hasattr(self, "lbl_status_base"):
            origem = (
                "pasta persistente do perfil do QGIS"
                if self.gpkg_path == self.gpkg_path_persistente
                else "pasta local do complemento (modo legado)"
            )
            self.lbl_status_base.setText(
                f"✅ Base de Referência instalada — {BASE_VERSAO}<br>"
                f"<small>Local: {origem}</small>"
            )
            self.btn_baixar_base.setText("Baixar novamente / Atualizar")
            self.btn_abrir_pasta_base.setEnabled(True)

        for layer_id, info in CAMADAS_BASE.items():
            uri = f"{self.gpkg_path}|layername={layer_id}"
            lyr = QgsVectorLayer(uri, layer_id, "ogr")
            self.status_layout.addWidget(CamadaStatusWidget(info["nome"], lyr.isValid()))

    def _selecionar_pasta(self):
        pasta = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Saída", os.path.expanduser("~"))
        if pasta:
            self.pasta_saida = pasta
            self.txt_pasta.setText(pasta)

    # ── Validações ───────────────────────────

    def _validar_cpf(self, cpf):
        cpf = re.sub(r'\D', '', cpf)
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        for i in range(9, 11):
            soma = sum(int(cpf[j]) * ((i + 1) - j) for j in range(i))
            if (soma * 10 % 11) % 10 != int(cpf[i]):
                return False
        return True

    def _validar_campos(self):
        erros = []
        if not self.txt_nome.text().strip():
            erros.append("• Nome do posseiro não informado.")
        if not self._validar_cpf(self.txt_cpf.text()):
            erros.append("• CPF inválido. Verifique o número digitado.")
        if not self.txt_posse.text().strip():
            erros.append("• Nome da posse/imóvel não informado.")
        if self.cmb_camada.currentData() is None:
            erros.append("• Nenhuma camada de polígono do imóvel selecionada.")
        if not self.pasta_saida:
            erros.append("• Pasta de saída não selecionada.")
        if not os.path.exists(self.gpkg_path):
            erros.append("• Base de Referência não instalada. Use a aba Base de Referência para baixá-la.")
        return erros

    # ── Processamento ────────────────────────

    def _processar(self):
        erros = self._validar_campos()
        if erros:
            QMessageBox.warning(self, "Campos obrigatórios",
                "Por favor, corrija os seguintes erros antes de continuar:\n\n" + "\n".join(erros))
            return
        self.btn_processar.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.txt_log.clear()
        self.log_msgs = []
        self._log("Iniciando processamento GeoCAR Amapá...", "info")
        try:
            self._executar_processamento()
        except Exception as e:
            self._log(f"Erro inesperado: {str(e)}", "erro")
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro durante o processamento:\n\n{str(e)}")
        finally:
            self.btn_processar.setEnabled(True)
            self.progress.setVisible(False)

    def _executar_processamento(self):
        nome      = self.txt_nome.text().strip()
        cpf       = self.txt_cpf.text().strip()
        posse     = self.txt_posse.text().strip()
        municipio = self.cmb_municipio.currentText()
        dt_agora  = datetime.now()
        posse_slug = posse.replace(' ', '_')

        layer_id = self.cmb_camada.currentData()
        layer_imovel = QgsProject.instance().mapLayer(layer_id)
        if not layer_imovel or not layer_imovel.isValid():
            self._log("Camada do imóvel inválida.", "erro")
            return

        crs_metrico = QgsCoordinateReferenceSystem("EPSG:31976")
        self._log(f"CRS original do imóvel: {layer_imovel.crs().authid()}", "info")

        if layer_imovel.crs().authid() != "EPSG:31976":
            self._log("Reprojetando camada do imóvel para SIRGAS 2000 UTM Zona 22S...", "info")
            imovel_proj = processing.run("native:reprojectlayer", {
                'INPUT': layer_imovel, 'TARGET_CRS': crs_metrico, 'OUTPUT': 'memory:'
            })['OUTPUT']
        else:
            imovel_proj = layer_imovel

        area_imovel_m2 = sum(f.geometry().area() for f in imovel_proj.getFeatures())
        area_imovel_ha = area_imovel_m2 / 10000
        self._log(f"Área total do imóvel: {area_imovel_ha:.4f} ha", "ok")
        self.progress.setValue(10)

        resultados = {
            "area_imovel_m2": area_imovel_m2,
            "area_imovel_ha": area_imovel_ha,
            "camadas": {},
            "reserva_legal": {},
            "hidrografia_encontrada": False,
            "hidrografia_categorias": [],
            "erros_camadas": [],
            "rvn_ha": 0,
            "total_rl_ha": 0,
            "deficit_ha": 0,
            "cenario_rl": 0,  # 1=suficiente, 2=insuficiente, 3=ausente
        }

        root = QgsProject.instance().layerTreeRoot()
        grupo = root.addGroup(f"GeoCAR — {posse}")

        # ── Clip camadas principais ──
        camadas_clip = ["area_antropizada", "area_consolidada", "servidao_administrativa", "vegetacao"]
        total_steps = len(camadas_clip) + 2
        step = 0

        for layer_key in camadas_clip:
            info = CAMADAS_BASE[layer_key]
            self._log(f"Processando: {info['nome']}...", "info")

            uri = f"{self.gpkg_path}|layername={layer_key}"
            lyr_base = QgsVectorLayer(uri, layer_key, "ogr")

            if not lyr_base.isValid():
                msg = f"{info['nome']} não encontrada no GeoPackage."
                self._log(msg, "aviso")
                resultados["erros_camadas"].append(msg)
                resultados["camadas"][layer_key] = {"area_m2": 0, "area_ha": 0}
                step += 1
                self.progress.setValue(10 + int(step / total_steps * 60))
                continue

            lyr_base_proj = processing.run("native:reprojectlayer", {
                'INPUT': lyr_base, 'TARGET_CRS': crs_metrico, 'OUTPUT': 'memory:'
            })['OUTPUT']

            clipped = processing.run("native:clip", {
                'INPUT': lyr_base_proj, 'OVERLAY': imovel_proj, 'OUTPUT': 'memory:'
            })['OUTPUT']

            if clipped.featureCount() == 0:
                msg = f"{info['nome']}: sem sobreposição com o imóvel."
                self._log(msg, "aviso")
                resultados["erros_camadas"].append(msg)
                resultados["camadas"][layer_key] = {"area_m2": 0, "area_ha": 0}
            else:
                area_m2 = sum(f.geometry().area() for f in clipped.getFeatures())
                area_ha = area_m2 / 10000
                resultados["camadas"][layer_key] = {"area_m2": area_m2, "area_ha": area_ha}
                self._log(f"{info['nome']}: {area_ha:.4f} ha", "ok")

                nome_arq = f"{layer_key}_{posse_slug}.shp"
                caminho_shp = os.path.join(self.pasta_saida, nome_arq)
                QgsVectorFileWriter.writeAsVectorFormat(
                    clipped, caminho_shp, "UTF-8", crs_metrico, "ESRI Shapefile"
                )
                lyr_add = QgsVectorLayer(caminho_shp, info["nome"], "ogr")
                if lyr_add.isValid():
                    QgsProject.instance().addMapLayer(lyr_add, False)
                    grupo.addLayer(lyr_add)

            step += 1
            self.progress.setValue(10 + int(step / total_steps * 60))

        # ── Hidrografia (buffer 500m + categorias) ──
        self._log("Calculando buffer de 500m para análise de hidrografia...", "info")

        uri_hidro = f"{self.gpkg_path}|layername=hidrografia"
        lyr_hidro = QgsVectorLayer(uri_hidro, "hidrografia", "ogr")

        if lyr_hidro.isValid():
            buffer_result = processing.run("native:buffer", {
                'INPUT': imovel_proj, 'DISTANCE': 500, 'SEGMENTS': 16, 'OUTPUT': 'memory:'
            })['OUTPUT']

            lyr_hidro_proj = processing.run("native:reprojectlayer", {
                'INPUT': lyr_hidro, 'TARGET_CRS': crs_metrico, 'OUTPUT': 'memory:'
            })['OUTPUT']

            hidro_clip = processing.run("native:clip", {
                'INPUT': lyr_hidro_proj, 'OVERLAY': buffer_result, 'OUTPUT': 'memory:'
            })['OUTPUT']

            if hidro_clip.featureCount() > 0:
                resultados["hidrografia_encontrada"] = True
                self._log("Hidrografia detectada na área de influência de 500m!", "ok")

                # Verificar se existe coluna 'categoria'
                campos = [f.name() for f in hidro_clip.fields()]
                tem_categoria = "categoria" in campos

                if tem_categoria:
                    # Coletar valores únicos de categoria (ignora vazios/nulos)
                    categorias = set()
                    for feat in hidro_clip.getFeatures():
                        val = feat["categoria"]
                        if val and str(val).strip():
                            categorias.add(str(val).strip())

                    if categorias:
                        self._log(f"Categorias encontradas: {', '.join(sorted(categorias))}", "info")
                        grupo_hidro = grupo.addGroup("Hidrografia (500m)")

                        for cat in sorted(categorias):
                            # Filtrar feições desta categoria
                            hidro_cat = processing.run("native:extractbyattribute", {
                                'INPUT': hidro_clip,
                                'FIELD': 'categoria',
                                'OPERATOR': 0,  # igual
                                'VALUE': cat,
                                'OUTPUT': 'memory:'
                            })['OUTPUT']

                            if hidro_cat.featureCount() > 0:
                                # Slug para nome de arquivo
                                slug = HIDRO_SLUG.get(cat, re.sub(r'[^a-zA-Z0-9]', '_', cat).lower())
                                nome_hidro = f"hidro_{slug}_{posse_slug}.shp"
                                caminho_hidro = os.path.join(self.pasta_saida, nome_hidro)
                                QgsVectorFileWriter.writeAsVectorFormat(
                                    hidro_cat, caminho_hidro, "UTF-8", crs_metrico, "ESRI Shapefile"
                                )
                                lyr_hidro_cat = QgsVectorLayer(caminho_hidro, f"Hidro — {cat}", "ogr")
                                if lyr_hidro_cat.isValid():
                                    QgsProject.instance().addMapLayer(lyr_hidro_cat, False)
                                    grupo_hidro.addLayer(lyr_hidro_cat)
                                    self._log(f"Hidrografia categoria '{cat}': salva.", "ok")
                                resultados["hidrografia_categorias"].append(cat)
                    else:
                        # Coluna categoria existe mas sem valores — salva clip único
                        self._salvar_hidro_unica(hidro_clip, posse_slug, crs_metrico, grupo, resultados)
                else:
                    # Sem coluna categoria — salva clip único
                    self._salvar_hidro_unica(hidro_clip, posse_slug, crs_metrico, grupo, resultados)
            else:
                self._log("Nenhuma hidrografia encontrada no raio de 500m.", "aviso")
        else:
            self._log("Camada de hidrografia não encontrada no GeoPackage.", "aviso")
            resultados["erros_camadas"].append("Hidrografia não encontrada no GeoPackage.")

        step += 1
        self.progress.setValue(10 + int(step / total_steps * 60))

        # ── Fitofisionomia (virtual) ──
        fito_checks = {
            "cerrado":  self.chk_cerrado.isChecked(),
            "floresta": self.chk_floresta.isChecked(),
            "campo":    self.chk_campo.isChecked(),
        }

        total_rl = 0.0
        for fito_key, marcado in fito_checks.items():
            if not marcado:
                continue
            info = CAMADAS_BASE[fito_key]
            self._log(f"Calculando área de {info['nome']} dentro do imóvel...", "info")

            uri_fito = f"{self.gpkg_path}|layername={fito_key}"
            lyr_fito = QgsVectorLayer(uri_fito, fito_key, "ogr")

            if not lyr_fito.isValid():
                msg = f"{info['nome']}: camada não encontrada no GeoPackage."
                self._log(msg, "aviso")
                resultados["erros_camadas"].append(msg)
                continue

            lyr_fito_proj = processing.run("native:reprojectlayer", {
                'INPUT': lyr_fito, 'TARGET_CRS': crs_metrico, 'OUTPUT': 'memory:'
            })['OUTPUT']

            intersect = processing.run("native:intersection", {
                'INPUT': lyr_fito_proj, 'OVERLAY': imovel_proj, 'OUTPUT': 'memory:'
            })['OUTPUT']

            area_m2 = sum(f.geometry().area() for f in intersect.getFeatures())
            area_ha = area_m2 / 10000
            fator = FATORES_RL[fito_key]
            rl_ha = area_ha * fator
            total_rl += rl_ha

            resultados["reserva_legal"][fito_key] = {
                "area_m2": area_m2,
                "area_ha": area_ha,
                "fator": fator,
                "rl_ha": rl_ha,
            }
            self._log(f"{info['nome']}: {area_ha:.4f} ha → RL estimada: {rl_ha:.4f} ha", "ok")

        resultados["total_rl_ha"] = total_rl

        step += 1
        self.progress.setValue(80)

        # ── RVN × RL — cenários ──
        rvn_ha = resultados["camadas"].get("vegetacao", {}).get("area_ha", 0)
        resultados["rvn_ha"] = rvn_ha

        if rvn_ha == 0:
            # Cenário 3 — sem RVN
            resultados["cenario_rl"] = 3
            resultados["deficit_ha"] = total_rl
            self._log("Nenhuma RVN encontrada no imóvel. RL deverá ser integralmente recomposta.", "aviso")

        elif rvn_ha >= total_rl:
            # Cenário 1 — RVN suficiente → camada vazia
            resultados["cenario_rl"] = 1
            resultados["deficit_ha"] = 0
            self._log(f"RVN ({rvn_ha:.4f} ha) é suficiente para cobrir a RL estimada ({total_rl:.4f} ha).", "ok")
            self._criar_rl_vazia(posse_slug, crs_metrico, grupo, posse)

        else:
            # Cenário 2 — RVN insuficiente → usa RVN como RL
            resultados["cenario_rl"] = 2
            resultados["deficit_ha"] = total_rl - rvn_ha
            self._log(f"RVN ({rvn_ha:.4f} ha) insuficiente. Déficit de {resultados['deficit_ha']:.4f} ha.", "aviso")

            # Copia shapefile da vegetação como Reserva Legal
            arq_rvn = os.path.join(self.pasta_saida, f"vegetacao_{posse_slug}.shp")
            arq_rl  = os.path.join(self.pasta_saida, f"Reserva_Legal_{posse_slug}.shp")

            uri_rvn = f"{self.gpkg_path}|layername=vegetacao"
            lyr_rvn_base = QgsVectorLayer(uri_rvn, "vegetacao", "ogr")
            if lyr_rvn_base.isValid():
                lyr_rvn_proj = processing.run("native:reprojectlayer", {
                    'INPUT': lyr_rvn_base, 'TARGET_CRS': crs_metrico, 'OUTPUT': 'memory:'
                })['OUTPUT']
                clipped_rvn = processing.run("native:clip", {
                    'INPUT': lyr_rvn_proj, 'OVERLAY': imovel_proj, 'OUTPUT': 'memory:'
                })['OUTPUT']
                QgsVectorFileWriter.writeAsVectorFormat(
                    clipped_rvn, arq_rl, "UTF-8", crs_metrico, "ESRI Shapefile"
                )
                lyr_rl = QgsVectorLayer(arq_rl, f"✅ Reserva Legal — {posse} (RVN total)", "ogr")
                if lyr_rl.isValid():
                    QgsProject.instance().addMapLayer(lyr_rl, False)
                    grupo.addLayer(lyr_rl)
                    self._log("Camada 'Reserva Legal' criada com a RVN completa do imóvel.", "ok")

        self.progress.setValue(90)

        # ── Relatórios ──
        self._gerar_relatorios(nome, cpf, posse, municipio, dt_agora, resultados)
        self.progress.setValue(100)

        self._log("Processamento concluído com sucesso!", "ok")
        QMessageBox.information(
            self, "✅ Processamento Concluído",
            f"O processamento do CAR foi concluído!\n\n"
            f"📁 Resultados em:\n{self.pasta_saida}\n\n"
            f"📋 Relatórios TXT e HTML gerados.\n"
            f"{'✏️ Delimite a Reserva Legal na camada vazia criada.' if resultados['cenario_rl'] == 1 else '⚠️ Verifique as orientações sobre Reserva Legal no relatório.'}"
        )

    def _salvar_hidro_unica(self, hidro_clip, posse_slug, crs_metrico, grupo, resultados):
        """Salva hidrografia como camada única (sem categorias)."""
        nome_hidro = f"hidrografia_{posse_slug}.shp"
        caminho_hidro = os.path.join(self.pasta_saida, nome_hidro)
        QgsVectorFileWriter.writeAsVectorFormat(
            hidro_clip, caminho_hidro, "UTF-8", crs_metrico, "ESRI Shapefile"
        )
        lyr_add = QgsVectorLayer(caminho_hidro, "Hidrografia (500m)", "ogr")
        if lyr_add.isValid():
            QgsProject.instance().addMapLayer(lyr_add, False)
            grupo.addLayer(lyr_add)
            self._log("Hidrografia salva (sem categorias).", "ok")
        resultados["hidrografia_categorias"] = []

    def _criar_rl_vazia(self, posse_slug, crs_metrico, grupo, posse):
        """Cria shapefile vazio para delimitação da Reserva Legal."""
        nome_rl = f"Reserva_Legal_{posse_slug}.shp"
        caminho_rl = os.path.join(self.pasta_saida, nome_rl)
        fields = QgsFields()
        fields.append(QgsField("id", QVariant.Int))
        fields.append(QgsField("area_ha", QVariant.Double))
        fields.append(QgsField("observacao", QVariant.String))
        writer = QgsVectorFileWriter(
            caminho_rl, "UTF-8", fields,
            QgsWkbTypes.MultiPolygon, crs_metrico, "ESRI Shapefile"
        )
        del writer
        lyr_rl = QgsVectorLayer(caminho_rl, f"✏️ Reserva Legal — {posse} (delimitar)", "ogr")
        if lyr_rl.isValid():
            QgsProject.instance().addMapLayer(lyr_rl, False)
            grupo.addLayer(lyr_rl)
            self._log("Camada vazia 'Reserva Legal' criada e pronta para edição.", "ok")

    # ── Relatórios ───────────────────────────

    def _gerar_relatorios(self, nome, cpf, posse, municipio, dt, resultados):
        dt_str  = dt.strftime("%d/%m/%Y às %H:%M:%S")
        dt_arq  = dt.strftime("%Y%m%d_%H%M%S")
        txt  = self._montar_txt(nome, cpf, posse, municipio, dt_str, resultados)
        html = self._montar_html(nome, cpf, posse, municipio, dt_str, resultados)
        base = f"Relatorio_CAR_{posse.replace(' ','_')}_{dt_arq}"
        with open(os.path.join(self.pasta_saida, base + ".txt"), "w", encoding="utf-8") as f:
            f.write(txt)
        with open(os.path.join(self.pasta_saida, base + ".html"), "w", encoding="utf-8") as f:
            f.write(html)
        self._log(f"Relatório TXT: {base}.txt", "ok")
        self._log(f"Relatório HTML: {base}.html", "ok")

    def _montar_txt(self, nome, cpf, posse, municipio, dt_str, r):
        L = []
        S  = "=" * 65
        S2 = "-" * 65

        L += [S,
              "         RELATÓRIO DE APOIO AO CADASTRO AMBIENTAL RURAL — GeoCAR Amapá",
              S,
              f"  Data e hora: {dt_str}", S2]

        L += ["\n1. IDENTIFICAÇÃO DO IMÓVEL\n",
              f"   Posseiro / Proprietário : {nome}",
              f"   CPF                     : {cpf}",
              f"   Nome da Posse / Imóvel  : {posse}",
              f"   Município               : {municipio} — Amapá (AP)",
              f"   Área total do imóvel    : {r['area_imovel_m2']:.2f} m²  |  {r['area_imovel_ha']:.4f} ha"]

        L += [f"\n{S2}", "\n2. ANÁLISE DAS CAMADAS AMBIENTAIS\n",
              "   As camadas abaixo foram recortadas a partir dos limites",
              "   do polígono do imóvel informado.\n"]

        nomes_map = {
            "area_antropizada":        "Área Antropizada",
            "area_consolidada":        "Área Consolidada",
            "servidao_administrativa": "Servidão Administrativa",
            "vegetacao":               "Rem. Vegetação Nativa (RVN)",
        }
        for key, nome_c in nomes_map.items():
            dados = r["camadas"].get(key, {})
            if dados.get("area_ha", 0) > 0:
                L.append(f"   {nome_c:<32}: {dados['area_m2']:.2f} m²  |  {dados['area_ha']:.4f} ha")
            else:
                L.append(f"   {nome_c:<32}: Sem sobreposição com o imóvel")

        L += [f"\n{S2}", "\n3. HIDROGRAFIA — ÁREA DE INFLUÊNCIA (500 metros)\n",
              "   Foi gerado um buffer virtual de 500 metros ao redor do",
              "   imóvel para verificar a presença de recursos hídricos",
              "   nas proximidades (Área de Preservação Permanente — APP).\n"]

        if r["hidrografia_encontrada"]:
            L.append("   ⚠️  ATENÇÃO: Hidrografia identificada dentro do raio de 500m.")
            if r["hidrografia_categorias"]:
                L.append("   Categorias encontradas:")
                for cat in r["hidrografia_categorias"]:
                    L.append(f"     • {cat}")
            else:
                L.append("   Camada salva sem categorias específicas.")
            L.append("   Verifique se há APP a ser declarada no CAR.")
        else:
            L.append("   ✅ Nenhuma hidrografia detectada no raio de 500m.")

        L += [f"\n{S2}", "\n4. FITOFISIONOMIA E ESTIMATIVA DE RESERVA LEGAL\n",
              "   O que é Reserva Legal?",
              "   ─────────────────────",
              "   A Reserva Legal (RL) é a área dentro do imóvel rural",
              "   que deve ser mantida com vegetação nativa, protegendo",
              "   a biodiversidade e os recursos hídricos. É obrigação",
              "   legal prevista no Código Florestal (Lei 12.651/2012).\n",
              "   Percentuais obrigatórios por fitofisionomia:",
              "     • Floresta na Amazônia Legal  → 80% da área de Floresta",
              "     • Cerrado na Amazônia Legal   → 35% da área de Cerrado",
              "     • Campo                       → 20% da área de Campo\n",
              "   Resultados calculados para este imóvel:\n"]

        nomes_fito = {"cerrado": "Cerrado", "floresta": "Floresta", "campo": "Campo"}
        if r.get("reserva_legal"):
            for key, dados in r["reserva_legal"].items():
                pct = int(dados['fator'] * 100)
                L += [f"   {nomes_fito[key]}",
                      f"     Área identificada no imóvel : {dados['area_ha']:.4f} ha",
                      f"     Percentual legal            : {pct}%",
                      f"     Reserva Legal estimada      : {dados['rl_ha']:.4f} ha\n"]
            L += [S2,
                  f"   TOTAL ESTIMADO DE RESERVA LEGAL: {r['total_rl_ha']:.4f} ha",
                  S2]
        else:
            L.append("   Nenhuma fitofisionomia marcada pelo usuário.")

        L += [f"\n{S2}", "\n5. REMANESCENTE DE VEGETAÇÃO NATIVA × RESERVA LEGAL\n"]

        rvn = r["rvn_ha"]
        rl  = r["total_rl_ha"]
        cen = r["cenario_rl"]

        L += [f"   RVN encontrada no imóvel    : {rvn:.4f} ha",
              f"   RL estimada (valor orientativo)     : {rl:.4f} ha\n"]

        if cen == 1:
            L += ["   ✅ SITUAÇÃO: RVN SUFICIENTE",
                  "   ─────────────────────────────────────────────────",
                  "   A vegetação nativa remanescente no imóvel é",
                  "   suficiente para cobrir a obrigação de Reserva Legal.",
                  "   O proprietário deve delimitar dentro da RVN uma área",
                  f"  de pelo menos {rl:.4f} ha para averbação como RL.",
                  "   Uma camada vazia foi criada no QGIS para isso."]
        elif cen == 2:
            L += [f"   ⚠️  SITUAÇÃO: RVN INSUFICIENTE — DÉFICIT DE {r['deficit_ha']:.4f} ha",
                  "   ─────────────────────────────────────────────────",
                  "   A vegetação nativa remanescente encontrada no imóvel",
                  "   é menor do que o exigido por lei. Por isso, toda a",
                  f"  RVN existente ({rvn:.4f} ha) foi automaticamente",
                  "   destinada como Reserva Legal e já está salva como",
                  "   camada no projeto QGIS.",
                  f"  O déficit restante de {r['deficit_ha']:.4f} ha deverá ser",
                  "   regularizado por meio de recomposição de vegetação",
                  "   nativa, compensação ou arrendamento de área de RL",
                  "   em outro imóvel, conforme art. 66 do Código Florestal."]
        else:
            L += ["   🚨 SITUAÇÃO CRÍTICA: SEM RVN NO IMÓVEL",
                  "   ─────────────────────────────────────────────────",
                  "   Nenhuma vegetação nativa remanescente foi encontrada",
                  "   dentro dos limites do imóvel. A Reserva Legal de",
                  f"  {rl:.4f} ha deverá ser integralmente recomposta",
                  "   por meio de restauração da vegetação nativa ou",
                  "   compensação em outro imóvel, conforme o Código",
                  "   Florestal (Lei 12.651/2012, art. 66)."]

        L += [f"\n{S2}", "\n6. PRÓXIMOS PASSOS — RESERVA LEGAL\n"]

        if cen == 1:
            L += ["   Uma camada vetorial vazia chamada 'Reserva Legal'",
                  "   foi criada no seu projeto QGIS. Use-a para delimitar",
                  "   no mapa a área destinada à RL, respeitando o tamanho",
                  f"  mínimo estimado de {rl:.4f} ha.",
                  "   A área deve estar dentro da RVN existente no imóvel."]
        elif cen == 2:
            L += ["   A camada 'Reserva Legal' foi criada automaticamente",
                  "   com toda a vegetação nativa remanescente do imóvel.",
                  "   Regularize o déficit conforme orientação técnica e",
                  "   legislação vigente antes da submissão do CAR."]
        else:
            L += ["   Nenhuma camada de Reserva Legal foi criada pois não",
                  "   há vegetação nativa no imóvel para ser destinada.",
                  "   Providencie a recomposição ou compensação da RL",
                  "   antes da regularização junto ao órgão ambiental competente."]

        L.append("\n   IMPORTANTE: Este relatório é uma estimativa técnica")
        L.append("   auxiliar. Consulte sempre um técnico ambiental")
        L.append("   habilitado antes da submissão oficial do CAR.\n")

        if r.get("erros_camadas"):
            L += [S2, "\n7. AVISOS E OCORRÊNCIAS\n"]
            for msg in r["erros_camadas"]:
                L.append(f"   ⚠️  {msg}")

        L += [f"\n{S}",
              "  Relatório gerado pelo complemento GeoCAR Amapá",
              f"  {dt_str}", S]

        return "\n".join(L)

    def _montar_html(self, nome, cpf, posse, municipio, dt_str, r):
        def tr(label, valor):
            return f"<tr><td class='lbl'>{label}</td><td>{valor}</td></tr>"

        nomes_map = {
            "area_antropizada":        "Área Antropizada",
            "area_consolidada":        "Área Consolidada",
            "servidao_administrativa": "Servidão Administrativa",
            "vegetacao":               "Rem. Vegetação Nativa (RVN)",
        }

        rows_camadas = ""
        for key, nome_c in nomes_map.items():
            dados = r["camadas"].get(key, {})
            if dados.get("area_ha", 0) > 0:
                rows_camadas += f"<tr><td>{nome_c}</td><td>{dados['area_m2']:,.2f} m²</td><td><strong>{dados['area_ha']:.4f} ha</strong></td></tr>"
            else:
                rows_camadas += f"<tr class='vazio'><td>{nome_c}</td><td colspan='2'>Sem sobreposição com o imóvel</td></tr>"

        nomes_fito = {"cerrado": "Cerrado", "floresta": "Floresta", "campo": "Campo"}
        rows_rl = ""
        if r.get("reserva_legal"):
            for key, dados in r["reserva_legal"].items():
                rows_rl += f"<tr><td>{nomes_fito[key]}</td><td>{dados['area_ha']:.4f} ha</td><td>{int(dados['fator']*100)}%</td><td><strong>{dados['rl_ha']:.4f} ha</strong></td></tr>"

        # Badge hidrografia
        if r["hidrografia_encontrada"]:
            cats = r.get("hidrografia_categorias", [])
            if cats:
                cats_html = "".join(f"<li>{c}</li>" for c in cats)
                hidro_html = f"<span class='badge-warn'>⚠️ Hidrografia detectada — {len(cats)} categoria(s)</span><ul style='margin-top:8px'>{cats_html}</ul>"
            else:
                hidro_html = "<span class='badge-warn'>⚠️ Hidrografia detectada (sem categorias)</span>"
        else:
            hidro_html = "<span class='badge-ok'>✅ Nenhuma hidrografia no raio de 500m</span>"

        # Seção RVN × RL
        rvn = r["rvn_ha"]
        rl  = r["total_rl_ha"]
        cen = r["cenario_rl"]

        if cen == 1:
            rvn_classe = "card-ok"
            rvn_titulo = "✅ RVN Suficiente"
            rvn_texto  = (f"A vegetação nativa remanescente no imóvel (<strong>{rvn:.4f} ha</strong>) é suficiente "
                          f"para cobrir a obrigação de Reserva Legal (<strong>{rl:.4f} ha</strong>). "
                          f"O proprietário deve delimitar dentro da RVN uma área de pelo menos <strong>{rl:.4f} ha</strong> "
                          f"para averbação como RL. Uma camada vazia foi criada no QGIS para este fim.")
            rl_instrucao = (f"Use a camada <strong>✏️ Reserva Legal — {posse}</strong> criada no projeto QGIS "
                            f"para desenhar no mapa a área destinada à RL, respeitando o mínimo de <strong>{rl:.4f} ha</strong>. "
                            f"A área deve estar dentro da vegetação nativa remanescente do imóvel.")
        elif cen == 2:
            rvn_classe = "card-warn"
            rvn_titulo = f"⚠️ RVN Insuficiente — Déficit de {r['deficit_ha']:.4f} ha"
            rvn_texto  = (f"A vegetação nativa remanescente encontrada (<strong>{rvn:.4f} ha</strong>) é menor "
                          f"do que o exigido por lei (<strong>{rl:.4f} ha</strong>). Por isso, toda a RVN existente "
                          f"foi automaticamente destinada como Reserva Legal e já está salva como camada no QGIS. "
                          f"O déficit de <strong>{r['deficit_ha']:.4f} ha</strong> deverá ser regularizado por meio de "
                          f"recomposição, compensação ou arrendamento conforme art. 66 do Código Florestal.")
            rl_instrucao = (f"A camada <strong>✅ Reserva Legal — {posse}</strong> foi criada automaticamente com "
                            f"toda a RVN do imóvel. Regularize o déficit de <strong>{r['deficit_ha']:.4f} ha</strong> "
                            f"junto ao órgão ambiental competente antes da submissão final do CAR.")
        else:
            rvn_classe = "card-critico"
            rvn_titulo = "🚨 Situação Crítica — Sem Vegetação Nativa no Imóvel"
            rvn_texto  = (f"Nenhuma vegetação nativa remanescente foi encontrada dentro dos limites do imóvel. "
                          f"A Reserva Legal de <strong>{rl:.4f} ha</strong> deverá ser integralmente recomposta "
                          f"por restauração da vegetação nativa ou compensação em outro imóvel, conforme o "
                          f"Código Florestal (Lei 12.651/2012, art. 66). Nenhuma camada foi criada.")
            rl_instrucao = (f"Providencie junto a um técnico ambiental habilitado o plano de recomposição ou "
                            f"compensação da Reserva Legal de <strong>{rl:.4f} ha</strong> antes da regularização "
                            f"no órgão ambiental competente.")

        total_rl_html = ""
        if r.get("total_rl_ha", 0) > 0:
            total_rl_html = f"<div class='total-rl'><span>Total estimado de Reserva Legal:</span><strong>{r['total_rl_ha']:.4f} ha</strong></div>"

        avisos_html = ""
        if r.get("erros_camadas"):
            itens = "".join(f"<li>{m}</li>" for m in r["erros_camadas"])
            avisos_html = f"<div class='secao'><h2>⚠️ Avisos e Ocorrências</h2><div class='card-warn'><ul>{itens}</ul></div></div>"

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório CAR — {posse}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#F1F8F1;color:#1A2E1A;font-size:14px}}
.container{{max-width:860px;margin:30px auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.12)}}
header{{background:linear-gradient(135deg,#1B5E20,#388E3C);color:white;padding:28px 32px}}
header h1{{font-size:22px;margin-bottom:4px}}
header p{{font-size:12px;color:#C8E6C9;margin-top:4px}}
.content{{padding:28px 32px}}
.secao{{margin-bottom:28px}}
.secao h2{{font-size:15px;font-weight:700;color:#1B5E20;border-left:5px solid #2E7D32;padding-left:12px;margin-bottom:14px}}
table{{width:100%;border-collapse:collapse;margin-top:8px}}
th{{background:#2E7D32;color:white;padding:10px 14px;text-align:left;font-size:13px}}
td{{padding:9px 14px;border-bottom:1px solid #E8F5E9;font-size:13px}}
td.lbl{{color:#4A7A4A;font-weight:600;width:42%}}
tr.vazio td{{color:#888;font-style:italic}}
.card-info{{background:#E8F5E9;border:1px solid #A5D6A7;border-radius:8px;padding:16px;margin-top:10px;font-size:13px;line-height:1.7;color:#2E4A2E}}
.card-ok{{background:#E8F5E9;border-left:5px solid #2E7D32;border-radius:6px;padding:16px;margin-top:10px;font-size:13px;line-height:1.7}}
.card-warn{{background:#FFF8E1;border-left:5px solid #F9A825;border-radius:6px;padding:16px;margin-top:10px;font-size:13px;line-height:1.7}}
.card-critico{{background:#FFEBEE;border-left:5px solid #C62828;border-radius:6px;padding:16px;margin-top:10px;font-size:13px;line-height:1.7}}
.card-ok h3{{color:#1B5E20;margin-bottom:8px}}
.card-warn h3{{color:#E65100;margin-bottom:8px}}
.card-critico h3{{color:#B71C1C;margin-bottom:8px}}
.badge-ok{{background:#E8F5E9;color:#2E7D32;border:1px solid #A5D6A7;padding:6px 14px;border-radius:20px;font-size:13px;font-weight:600}}
.badge-warn{{background:#FFF8E1;color:#E65100;border:1px solid #FFCC02;padding:6px 14px;border-radius:20px;font-size:13px;font-weight:600}}
.total-rl{{background:#1B5E20;color:white;border-radius:8px;padding:14px 20px;display:flex;justify-content:space-between;align-items:center;margin-top:14px;font-size:14px}}
.total-rl strong{{font-size:20px}}
.rl-box{{background:#FFF8E1;border:2px solid #F9A825;border-radius:8px;padding:16px;margin-top:14px;font-size:13px;line-height:1.7;color:#4A3700}}
footer{{background:#E8F5E9;padding:16px 32px;text-align:center;font-size:12px;color:#4A7A4A;border-top:2px solid #C8E6C9}}
</style>
</head>
<body>
<div class="container">
<header>
  <h1>🌿 Relatório de Apoio ao CAR</h1>
  <p>📅 Gerado em: {dt_str}</p>
</header>
<div class="content">

<div class="secao">
  <h2>1. Identificação do Imóvel</h2>
  <table>
    {tr("Posseiro / Proprietário", nome)}
    {tr("CPF", cpf)}
    {tr("Nome da Posse / Imóvel", posse)}
    {tr("Município", f"{municipio} — Amapá (AP)")}
    {tr("Área total do imóvel", f"{r['area_imovel_m2']:,.2f} m² &nbsp;|&nbsp; <strong>{r['area_imovel_ha']:.4f} ha</strong>")}
  </table>
</div>

<div class="secao">
  <h2>2. Resultados do Recorte das Camadas de Referência</h2>
  <p style="font-size:13px;color:#4A6741;margin-bottom:10px">Camadas recortadas a partir dos limites do polígono do imóvel.</p>
  <table>
    <tr><th>Camada</th><th>Área (m²)</th><th>Área (ha)</th></tr>
    {rows_camadas}
  </table>
</div>

<div class="secao">
  <h2>3. Hidrografia — Área de Influência (500 metros)</h2>
  <div class="card-info">
    Foi realizado um <strong>buffer virtual de 500 metros</strong> ao redor do imóvel para verificar
    a presença de recursos hídricos nas proximidades, relacionados à
    <strong>Área de Preservação Permanente (APP)</strong> conforme o Código Florestal (Lei 12.651/2012).<br><br>
    {hidro_html}
  </div>
</div>

<div class="secao">
  <h2>4. Fitofisionomia e Estimativa de Reserva Legal</h2>
  <div class="card-info" style="margin-bottom:14px">
    <strong>O que é Reserva Legal?</strong><br>
    A Reserva Legal (RL) é a área dentro do imóvel rural que deve ser mantida com vegetação nativa,
    protegendo a biodiversidade e os recursos hídricos. É obrigação legal pelo Código Florestal
    (Lei nº 12.651/2012). O percentual exigido depende da fitofisionomia predominante:
    <ul style="margin-top:8px;padding-left:18px;line-height:1.9">
      <li><strong>Floresta na Amazônia Legal:</strong> 80% da área de Floresta</li>
      <li><strong>Cerrado na Amazônia Legal:</strong> 35% da área de Cerrado</li>
      <li><strong>Campo:</strong> 20% da área de Campo</li>
    </ul>
  </div>
  {"<table><tr><th>Fitofisionomia</th><th>Área no imóvel</th><th>% Legal</th><th>RL estimada</th></tr>" + rows_rl + "</table>" if rows_rl else "<p style='color:#888;font-style:italic'>Nenhuma fitofisionomia informada.</p>"}
  {total_rl_html}
</div>

<div class="secao">
  <h2>5. Remanescente de Vegetação Nativa × Reserva Legal</h2>
  <table style="margin-bottom:14px">
    {tr("RVN encontrada no imóvel", f"<strong>{rvn:.4f} ha</strong>")}
    {tr("RL estimada (valor orientativo)", f"<strong>{rl:.4f} ha</strong>")}
  </table>
  <div class="{rvn_classe}">
    <h3>{rvn_titulo}</h3>
    {rvn_texto}
  </div>
</div>

<div class="secao">
  <h2>6. Próximos Passos — Reserva Legal</h2>
  <div class="rl-box">
    {rl_instrucao}<br><br>
    <strong>⚠️ Atenção:</strong> Os valores apresentados são uma <strong>estimativa técnica auxiliar</strong>.
    A averbação oficial da Reserva Legal deve seguir todos os critérios do CAR e da legislação ambiental vigente.
    Consulte sempre um técnico ambiental habilitado antes da submissão final.
  </div>
</div>

{avisos_html}

</div>
<footer>
  Relatório gerado pelo complemento <strong>GeoCAR Amapá</strong> · {dt_str}
</footer>
</div>
</body>
</html>"""

    # ── Carregar Base de Referência ───────────

    def _carregar_base_referencia(self):
        if not os.path.exists(self.gpkg_path):
            QMessageBox.warning(self, "Arquivo não encontrado",
                "A Base de Referência ainda não está instalada.\n\n"
                "Use o botão 'Baixar Base de Referência' nesta aba.")
            return

        root = QgsProject.instance().layerTreeRoot()
        grupo_nome = "Base de Referência CAR — Amapá"
        existente = root.findGroup(grupo_nome)
        if existente:
            root.removeChildNode(existente)

        grupo = root.insertGroup(0, grupo_nome)
        carregadas = 0

        for layer_key, info in CAMADAS_BASE.items():
            uri = f"{self.gpkg_path}|layername={layer_key}"
            lyr = QgsVectorLayer(uri, info["nome"], "ogr")
            if lyr.isValid():
                QgsProject.instance().addMapLayer(lyr, False)
                grupo.addLayer(lyr)
                carregadas += 1
                self._log(f"Camada carregada: {info['nome']}", "ok")
            else:
                self._log(f"Não foi possível carregar: {info['nome']}", "aviso")

        if carregadas > 0:
            QMessageBox.information(self, "✅ Base Carregada",
                f"{carregadas} camada(s) carregadas com sucesso no grupo\n'{grupo_nome}'.")
        else:
            QMessageBox.warning(self, "Nenhuma camada carregada",
                "Nenhuma camada pôde ser carregada. Verifique o GeoPackage.")
