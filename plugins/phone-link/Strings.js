.pragma library

var languages = ["de", "es", "fr", "ja", "ko", "pt_BR", "zh_CN"];
var entries = {
    "Done.": ["Fertig.", "Listo.", "Terminé.", "完了。", "완료.", "Concluído.", "完成。"],
    "Actions": ["Aktionen", "Acciones", "Actions", "操作", "작업", "Ações", "操作"],
    "Hide actions": ["Aktionen ausblenden", "Ocultar acciones", "Masquer les actions", "操作を隠す", "작업 숨기기", "Ocultar ações", "隐藏操作"],
    "Connected": ["Verbunden", "Conectado", "Connecté", "接続済み", "연결됨", "Conectado", "已连接"],
    "Charging": ["Wird geladen", "Cargando", "En charge", "充電中", "충전 중", "Carregando", "充电中"],
    "On battery": ["Akkubetrieb", "Con batería", "Sur batterie", "バッテリー使用中", "배터리 사용 중", "Na bateria", "使用电池"],
    "Offline": ["Offline", "Sin conexión", "Hors ligne", "オフライン", "오프라인", "Desconectado", "离线"],
    "Available": ["Verfügbar", "Disponible", "Disponible", "利用可能", "사용 가능", "Disponível", "可用"],
    "Pairing request": ["Kopplungsanfrage", "Solicitud de vinculación", "Demande d’association", "ペアリング要求", "페어링 요청", "Pedido de pareamento", "配对请求"],
    "Waiting for phone": ["Warte auf Telefon", "Esperando al teléfono", "En attente du téléphone", "スマートフォンの応答待ち", "휴대폰 응답 대기 중", "Aguardando o telefone", "等待手机"],
    "Accept only if this is your phone. Compare the pairing code on both devices.": ["Nur für Ihr eigenes Telefon annehmen. Vergleichen Sie den Kopplungscode auf beiden Geräten.", "Acepta solo si es tu teléfono. Compara el código de vinculación en ambos dispositivos.", "Acceptez uniquement votre téléphone. Comparez le code d’association sur les deux appareils.", "自分のスマートフォンの場合のみ承認してください。両方の機器でペアリングコードを確認してください。", "본인 휴대폰인 경우에만 수락하세요. 두 기기의 페어링 코드를 비교하세요.", "Aceite apenas se este for seu telefone. Compare o código de pareamento nos dois dispositivos.", "请仅接受您自己的手机。比较两台设备上的配对码。"],
    "Accept": ["Annehmen", "Aceptar", "Accepter", "承認", "수락", "Aceitar", "接受"],
    "Reject": ["Ablehnen", "Rechazar", "Refuser", "拒否", "거부", "Rejeitar", "拒绝"],
    "Pair": ["Koppeln", "Vincular", "Associer", "ペアリング", "페어링", "Parear", "配对"],
    "Unpair": ["Entkoppeln", "Desvincular", "Dissocier", "ペアリング解除", "페어링 해제", "Desparear", "取消配对"],
    "Send files": ["Dateien senden", "Enviar archivos", "Envoyer des fichiers", "ファイルを送信", "파일 보내기", "Enviar arquivos", "发送文件"],
    "Send clipboard": ["Zwischenablage senden", "Enviar portapapeles", "Envoyer le presse-papiers", "クリップボードを送信", "클립보드 보내기", "Enviar área de transferência", "发送剪贴板"],
    "Ring my phone": ["Telefon klingeln lassen", "Hacer sonar mi teléfono", "Faire sonner mon téléphone", "スマートフォンを鳴らす", "내 휴대폰 울리기", "Tocar meu telefone", "响铃查找手机"],
    "Ping": ["Ping", "Ping", "Ping", "Ping", "핑", "Ping", "Ping"],
    "Browse files": ["Dateien durchsuchen", "Explorar archivos", "Parcourir les fichiers", "ファイルを閲覧", "파일 찾아보기", "Explorar arquivos", "浏览文件"],
    "Disabled actions are not shared by this phone.": ["Deaktivierte Aktionen werden von diesem Telefon nicht freigegeben.", "Este teléfono no comparte las acciones desactivadas.", "Ce téléphone ne partage pas les actions désactivées.", "無効な操作は、このスマートフォンで共有されていません。", "비활성화된 작업은 이 휴대폰에서 공유되지 않습니다.", "As ações desativadas não são compartilhadas por este telefone.", "此手机未共享已禁用的操作。"],
    "Unpair this device? You will need to pair it again to reconnect.": ["Dieses Gerät entkoppeln? Zum erneuten Verbinden müssen Sie es wieder koppeln.", "¿Desvincular este dispositivo? Tendrás que vincularlo de nuevo para reconectarlo.", "Dissocier cet appareil ? Vous devrez l’associer à nouveau pour le reconnecter.", "この機器のペアリングを解除しますか？再接続には再度ペアリングが必要です。", "이 기기의 페어링을 해제할까요? 다시 연결하려면 페어링해야 합니다.", "Desparear este dispositivo? Será necessário pareá-lo novamente para reconectar.", "取消此设备的配对？重新连接时需要再次配对。"],
    "Confirm unpair": ["Entkoppeln bestätigen", "Confirmar desvinculación", "Confirmer la dissociation", "解除を確認", "해제 확인", "Confirmar despareamento", "确认取消配对"],
    "Cancel": ["Abbrechen", "Cancelar", "Annuler", "キャンセル", "취소", "Cancelar", "取消"],
    "Checking KDE Connect…": ["KDE Connect wird geprüft…", "Comprobando KDE Connect…", "Vérification de KDE Connect…", "KDE Connect を確認中…", "KDE Connect 확인 중…", "Verificando o KDE Connect…", "正在检查 KDE Connect…"],
    "Install KDE Connect through the plugin's package review.": ["Installieren Sie KDE Connect über die Paketprüfung des Plugins.", "Instala KDE Connect desde la revisión de paquetes del complemento.", "Installez KDE Connect via la validation des paquets du plugin.", "プラグインのパッケージ確認から KDE Connect をインストールしてください。", "플러그인의 패키지 검토에서 KDE Connect를 설치하세요.", "Instale o KDE Connect pela revisão de pacotes do plugin.", "请通过插件的安装包审核安装 KDE Connect。"],
    "KDE Connect is not running. Start it to discover phones on your local network.": ["KDE Connect läuft nicht. Starten Sie es, um Telefone im lokalen Netzwerk zu finden.", "KDE Connect no está en ejecución. Inícialo para descubrir teléfonos en tu red local.", "KDE Connect est arrêté. Démarrez-le pour découvrir les téléphones du réseau local.", "KDE Connect が起動していません。起動してローカルネットワークのスマートフォンを探してください。", "KDE Connect가 실행 중이 아닙니다. 시작하여 로컬 네트워크에서 휴대폰을 찾으세요.", "O KDE Connect não está em execução. Inicie-o para descobrir telefones na rede local.", "KDE Connect 未运行。启动它以发现局域网中的手机。"],
    "KDE Connect is not answering. Check the session D-Bus and try again.": ["KDE Connect antwortet nicht. Prüfen Sie den Sitzungs-D-Bus und versuchen Sie es erneut.", "KDE Connect no responde. Comprueba el D-Bus de sesión e inténtalo de nuevo.", "KDE Connect ne répond pas. Vérifiez le D-Bus de session et réessayez.", "KDE Connect が応答しません。セッション D-Bus を確認して再試行してください。", "KDE Connect가 응답하지 않습니다. 세션 D-Bus를 확인하고 다시 시도하세요.", "O KDE Connect não está respondendo. Verifique o D-Bus da sessão e tente novamente.", "KDE Connect 无响应。请检查会话 D-Bus 后重试。"],
    "Open KDE Connect on your phone and join the same local network.": ["Öffnen Sie KDE Connect auf Ihrem Telefon und verbinden Sie es mit demselben lokalen Netzwerk.", "Abre KDE Connect en tu teléfono y conéctate a la misma red local.", "Ouvrez KDE Connect sur votre téléphone et rejoignez le même réseau local.", "スマートフォンで KDE Connect を開き、同じローカルネットワークに接続してください。", "휴대폰에서 KDE Connect를 열고 같은 로컬 네트워크에 연결하세요.", "Abra o KDE Connect no telefone e conecte-se à mesma rede local.", "在手机上打开 KDE Connect 并连接到同一局域网。"],
    "Start KDE Connect": ["KDE Connect starten", "Iniciar KDE Connect", "Démarrer KDE Connect", "KDE Connect を起動", "KDE Connect 시작", "Iniciar KDE Connect", "启动 KDE Connect"],
    "No devices found. Keep the phone app open for discovery.": ["Keine Geräte gefunden. Lassen Sie die Telefon-App zur Suche geöffnet.", "No se encontraron dispositivos. Mantén abierta la app del teléfono para descubrirlos.", "Aucun appareil trouvé. Gardez l’application du téléphone ouverte pour la découverte.", "機器が見つかりません。スマートフォンのアプリを開いたままにしてください。", "기기를 찾지 못했습니다. 검색을 위해 휴대폰 앱을 열어 두세요.", "Nenhum dispositivo encontrado. Mantenha o aplicativo do telefone aberto para a descoberta.", "未找到设备。请保持手机应用打开以便发现设备。"],
    "Some devices could not be shown. Open KDE Connect for the complete list.": ["Einige Geräte konnten nicht angezeigt werden. Öffnen Sie KDE Connect für die vollständige Liste.", "No se pudieron mostrar algunos dispositivos. Abre KDE Connect para ver la lista completa.", "Certains appareils n’ont pas pu être affichés. Ouvrez KDE Connect pour la liste complète.", "一部の機器を表示できませんでした。全一覧は KDE Connect で確認してください。", "일부 기기를 표시하지 못했습니다. 전체 목록은 KDE Connect에서 확인하세요.", "Alguns dispositivos não puderam ser exibidos. Abra o KDE Connect para ver a lista completa.", "部分设备无法显示。请打开 KDE Connect 查看完整列表。"],
    "Choose files in the desktop dialog…": ["Dateien im Desktop-Dialog auswählen…", "Elige archivos en el diálogo del escritorio…", "Choisissez les fichiers dans la boîte de dialogue…", "デスクトップのダイアログでファイルを選択してください…", "데스크톱 대화상자에서 파일을 선택하세요…", "Escolha os arquivos na janela do sistema…", "请在桌面对话框中选择文件…"],
    "Working…": ["Wird ausgeführt…", "Procesando…", "En cours…", "処理中…", "처리 중…", "Processando…", "处理中…"],
    "Request sent. Check your phone.": ["Anfrage gesendet. Prüfen Sie Ihr Telefon.", "Solicitud enviada. Revisa tu teléfono.", "Demande envoyée. Vérifiez votre téléphone.", "要求を送信しました。スマートフォンを確認してください。", "요청을 보냈습니다. 휴대폰을 확인하세요.", "Solicitação enviada. Verifique seu telefone.", "请求已发送。请查看手机。"],
    "Action failed. Check the phone, permissions and KDE Connect.": ["Aktion fehlgeschlagen. Prüfen Sie Telefon, Berechtigungen und KDE Connect.", "La acción falló. Revisa el teléfono, los permisos y KDE Connect.", "Échec de l’action. Vérifiez le téléphone, les autorisations et KDE Connect.", "操作に失敗しました。スマートフォン、権限、KDE Connect を確認してください。", "작업에 실패했습니다. 휴대폰, 권한 및 KDE Connect를 확인하세요.", "A ação falhou. Verifique o telefone, as permissões e o KDE Connect.", "操作失败。请检查手机、权限及 KDE Connect。"],
    "Eitr's firewall already lets KDE Connect through on your local network.": ["Die Firewall von Eitr lässt KDE Connect in Ihrem lokalen Netzwerk bereits zu.", "El cortafuegos de Eitr ya permite KDE Connect en tu red local.", "Le pare-feu d’Eitr autorise déjà KDE Connect sur votre réseau local.", "Eitr のファイアウォールは、ローカルネットワークで KDE Connect の通信をすでに許可しています。", "Eitr 방화벽은 로컬 네트워크에서 KDE Connect 통신을 이미 허용합니다.", "O firewall do Eitr já permite o KDE Connect na sua rede local.", "Eitr 的防火墙已允许 KDE Connect 在您的局域网中通信。"],
    "No phone connected": ["Kein Telefon verbunden", "Ningún teléfono conectado", "Aucun téléphone connecté", "スマートフォン未接続", "연결된 휴대폰 없음", "Nenhum telefone conectado", "未连接手机"]
};

function tr(source) {
    const locale = Qt.locale().name;
    let index = languages.indexOf(locale);
    if (index === -1) index = languages.indexOf(locale.split("_")[0]);
    return index !== -1 && entries[source] ? entries[source][index] : source;
}
