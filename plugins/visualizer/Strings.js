.pragma library

var languages = ["de", "es", "fr", "ja", "ko", "pt_BR", "zh_CN"];
var entries = {
    "Wave": ["Welle", "Onda", "Onde", "波形", "파형", "Onda", "波形"],
    "Bars": ["Balken", "Barras", "Barres", "バー", "막대", "Barras", "柱状"],
    "Ring": ["Ring", "Anillo", "Anneau", "リング", "링", "Anel", "圆环"],
    "Mirror": ["Spiegel", "Espejo", "Miroir", "ミラー", "미러", "Espelho", "镜像"],
    "Dots": ["Punkte", "Puntos", "Points", "ドット", "점", "Pontos", "圆点"],
    "Accent": ["Akzent", "Acento", "Accent", "アクセント", "강조 색상", "Destaque", "强调色"],
    "Palette": ["Palette", "Paleta", "Palette", "パレット", "팔레트", "Paleta", "调色板"],
    "Colors": ["Farben", "Colores", "Couleurs", "色", "색상", "Cores", "颜色"]
};

var keys = Object.keys(entries);
var translations = {};
for (var langIndex = 0; langIndex < languages.length; ++langIndex) {
    var lang = languages[langIndex];
    translations[lang] = keys.map(function(key) { return entries[key][langIndex]; });
}

function tr(source, locale) {
    var language = locale || (typeof Qt !== "undefined" && Qt.locale ? Qt.locale().name : "en_US");
    var index = languages.indexOf(language);
    if (index === -1) index = languages.indexOf(String(language).split("_")[0]);
    return index !== -1 && entries[source] ? entries[source][index] : source;
}

if (typeof module !== "undefined") {
    module.exports = {
        languages: languages,
        entries: entries,
        keys: keys,
        translations: translations,
        tr: tr
    };
}
