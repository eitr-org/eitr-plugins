.pragma library
// Plugin translations stay with the reviewed plugin, without modifying Eitr's catalog.
var languages = ["de", "es", "fr", "ja", "ko", "pt", "zh"];
var translations = {
"Memory split unavailable": ["Speicheraufteilung unbekannt", "Reparto de memoria no disponible", "Répartition mémoire indisponible", "メモリ内訳は不明", "메모리 구분 정보 없음", "Divisão de memória indisponível", "内存分配信息不可用"],
"Already installed": ["Bereits installiert", "Ya instalado", "Déjà installé", "インストール済み", "이미 설치됨", "Já instalado", "已安装"],
"Unload": ["Entladen", "Descargar de memoria", "Décharger", "メモリから解放", "메모리 해제", "Descarregar", "卸载出内存"],
"Delete": ["Löschen", "Eliminar", "Supprimer", "削除", "삭제", "Excluir", "删除"],
"Download a model": ["Modell herunterladen", "Descargar un modelo", "Télécharger un modèle", "モデルをダウンロード", "모델 다운로드", "Baixar um modelo", "下载模型"],
"Suggestions": ["Vorschläge", "Sugerencias", "Suggestions", "候補", "추천", "Sugestões", "推荐"],
"Approximate downloads; sizes can change.": ["Ungefähre Downloadgrößen; Änderungen möglich.", "Tamaños aproximados; pueden cambiar.", "Tailles approximatives, susceptibles de changer.", "ダウンロードサイズは概算です。", "다운로드 크기는 대략적인 값입니다.", "Tamanhos aproximados; podem mudar.", "下载大小为估计值，可能变化。"],
"Model name, e.g. llama3.2:3b": ["Modellname, z. B. llama3.2:3b", "Modelo, p. ej. llama3.2:3b", "Modèle, ex. llama3.2:3b", "モデル名（例：llama3.2:3b）", "모델 이름 (예: llama3.2:3b)", "Modelo, ex.: llama3.2:3b", "模型名称，如 llama3.2:3b"],
"Download": ["Herunterladen", "Descargar", "Télécharger", "ダウンロード", "다운로드", "Baixar", "下载"],
"Downloading": ["Wird heruntergeladen", "Descargando", "Téléchargement", "ダウンロード中", "다운로드 중", "Baixando", "下载中"],
"Complete": ["Abgeschlossen", "Completado", "Terminé", "完了", "완료", "Concluído", "完成"],
"Cancelled": ["Abgebrochen", "Cancelado", "Annulé", "キャンセル済み", "취소됨", "Cancelado", "已取消"],
"Interrupted — retry to resume": ["Unterbrochen – zum Fortsetzen erneut versuchen", "Interrumpido; reintenta para continuar", "Interrompu ; réessayez pour reprendre", "中断しました。再試行で再開", "중단됨 — 다시 시도하여 계속", "Interrompido — tente novamente para retomar", "已中断，重试以继续"],
"Download failed — retry": ["Download fehlgeschlagen – erneut versuchen", "Descarga fallida; reintenta", "Échec du téléchargement ; réessayez", "ダウンロード失敗。再試行してください", "다운로드 실패 — 다시 시도", "Falha no download — tente novamente", "下载失败，请重试"],
"Cancel": ["Abbrechen", "Cancelar", "Annuler", "キャンセル", "취소", "Cancelar", "取消"],
"Preparing download…": ["Download wird vorbereitet…", "Preparando descarga…", "Préparation du téléchargement…", "準備中…", "다운로드 준비 중…", "Preparando download…", "正在准备下载…"],
"Downloads continue when this panel closes.": ["Downloads laufen bei geschlossenem Panel weiter.", "Las descargas continúan al cerrar el panel.", "Les téléchargements continuent après fermeture du panneau.", "パネルを閉じてもダウンロードは続きます。", "패널을 닫아도 다운로드가 계속됩니다.", "Os downloads continuam ao fechar este painel.", "关闭面板后下载会继续。"],
"Done": ["Erledigt", "Listo", "Terminé", "完了", "완료", "Pronto", "完成"],
"Operation failed. Check the service and model name.": ["Aktion fehlgeschlagen. Dienst und Modellnamen prüfen.", "La operación falló. Comprueba el servicio y el modelo.", "Échec. Vérifiez le service et le nom du modèle.", "操作に失敗しました。サービスとモデル名を確認してください。", "작업 실패. 서비스와 모델 이름을 확인하세요.", "Falha na operação. Confira o serviço e o nome do modelo.", "操作失败。请检查服务和模型名称。"],
"Checking status…": ["Status wird geprüft…", "Comprobando estado…", "Vérification de l’état…", "状態を確認中…", "상태 확인 중…", "Verificando estado…", "正在检查状态…"],
"Setup needed": ["Einrichtung erforderlich", "Requiere configuración", "Configuration requise", "セットアップが必要", "설정 필요", "Configuração necessária", "需要设置"],
"Running": ["Läuft", "En ejecución", "En cours", "実行中", "실행 중", "Em execução", "运行中"],
"Stopped": ["Gestoppt", "Detenido", "Arrêté", "停止中", "중지됨", "Parado", "已停止"],
"Set up": ["Einrichten", "Configurar", "Configurer", "セットアップ", "설정", "Configurar", "设置"],
"Stop": ["Stoppen", "Detener", "Arrêter", "停止", "중지", "Parar", "停止"],
"Start": ["Starten", "Iniciar", "Démarrer", "開始", "시작", "Iniciar", "启动"],
"Choose Ollama in Eitr’s Default Assistant setup. It installs and configures the local assistant after confirmation.": ["Ollama in Eitrs Standardassistent-Einrichtung wählen. Installation und Einrichtung erfolgen nach Bestätigung.", "Elige Ollama en Asistente predeterminado de Eitr. Se instala y configura tras confirmar.", "Choisissez Ollama dans l’assistant par défaut d’Eitr. Il sera installé et configuré après confirmation.", "Eitrの既定のアシスタント設定でOllamaを選択してください。確認後にインストールと設定が行われます。", "Eitr 기본 어시스턴트 설정에서 Ollama를 선택하세요. 확인 후 설치하고 설정합니다.", "Escolha Ollama na configuração de Assistente Padrão do Eitr. A instalação e configuração ocorrem após confirmação.", "在 Eitr 的默认助手设置中选择 Ollama，确认后将安装并配置本地助手。"],
"Eitr’s local model:": ["Eitrs lokales Modell:", "Modelo local de Eitr:", "Modèle local d’Eitr :", "Eitrのローカルモデル：", "Eitr 로컬 모델:", "Modelo local do Eitr:", "Eitr 的本地模型："],
"Eitr does not offer a model chooser yet.": ["Eitr bietet noch keine Modellauswahl.", "Eitr aún no permite elegir modelo.", "Eitr ne permet pas encore de choisir le modèle.", "Eitrはまだモデル選択に対応していません。", "Eitr는 아직 모델 선택을 지원하지 않습니다.", "O Eitr ainda não oferece seleção de modelo.", "Eitr 尚不支持选择模型。"],
"Status unavailable. Check the user service.": ["Status unbekannt. Benutzerdienst prüfen.", "Estado no disponible. Comprueba el servicio de usuario.", "État indisponible. Vérifiez le service utilisateur.", "状態を取得できません。ユーザーサービスを確認してください。", "상태를 확인할 수 없습니다. 사용자 서비스를 확인하세요.", "Estado indisponível. Confira o serviço do usuário.", "无法获取状态。请检查用户服务。"],
"Loaded models": ["Geladene Modelle", "Modelos en memoria", "Modèles chargés", "読み込み済みモデル", "메모리에 로드된 모델", "Modelos carregados", "已加载模型"],
"No models loaded": ["Keine Modelle geladen", "Ningún modelo en memoria", "Aucun modèle chargé", "読み込み済みモデルなし", "로드된 모델 없음", "Nenhum modelo carregado", "没有已加载模型"],
"Installed models": ["Installierte Modelle", "Modelos instalados", "Modèles installés", "インストール済みモデル", "설치된 모델", "Modelos instalados", "已安装模型"],
"No installed models": ["Keine Modelle installiert", "Ningún modelo instalado", "Aucun modèle installé", "インストール済みモデルなし", "설치된 모델 없음", "Nenhum modelo instalado", "没有已安装模型"],
"Delete model?": ["Modell löschen?", "¿Eliminar modelo?", "Supprimer le modèle ?", "モデルを削除しますか？", "모델을 삭제할까요?", "Excluir modelo?", "删除模型？"],
"This removes its local download. Download it again to restore it.": ["Der lokale Download wird entfernt. Zum Wiederherstellen erneut herunterladen.", "Se elimina la copia local. Descárgala de nuevo para restaurarla.", "La copie locale sera supprimée. Téléchargez-la à nouveau pour la restaurer.", "ローカルのデータを削除します。復元するには再ダウンロードが必要です。", "로컬 다운로드를 삭제합니다. 복원하려면 다시 다운로드하세요.", "Isso remove a cópia local. Baixe novamente para restaurar.", "这将删除本地副本。重新下载即可恢复。"],
"This is Eitr’s local model. Local chat will need setup again.": ["Dies ist Eitrs lokales Modell. Der lokale Chat muss erneut eingerichtet werden.", "Es el modelo local de Eitr. El chat local requerirá configurarse otra vez.", "C’est le modèle local d’Eitr. Le chat local devra être reconfiguré.", "Eitrのローカルモデルです。ローカルチャットは再セットアップが必要になります。", "Eitr 로컬 모델입니다. 로컬 채팅을 다시 설정해야 합니다.", "Este é o modelo local do Eitr. Será necessário configurar o chat local novamente.", "这是 Eitr 的本地模型。本地聊天将需要重新设置。"],
"Confirm delete": ["Löschen bestätigen", "Confirmar eliminación", "Confirmer la suppression", "削除を確定", "삭제 확인", "Confirmar exclusão", "确认删除"],
"Open Chat": ["Chat öffnen", "Abrir chat", "Ouvrir le chat", "チャットを開く", "채팅 열기", "Abrir chat", "打开聊天"],
"Opens your default assistant, just like SUPER + A.": ["Öffnet den Standardassistenten wie SUPER + A.", "Abre tu asistente predeterminado, como SUPER + A.", "Ouvre votre assistant par défaut, comme SUPER + A.", "SUPER + Aと同じ既定のアシスタントを開きます。", "SUPER + A처럼 기본 어시스턴트를 엽니다.", "Abre seu assistente padrão, como SUPER + A.", "与 SUPER + A 一样打开默认助手。"]
};
function tr(text) {
    const language = Qt.locale().name.split("_")[0];
    const index = languages.indexOf(language);
    return index >= 0 && translations[text] ? translations[text][index] : text;
}
