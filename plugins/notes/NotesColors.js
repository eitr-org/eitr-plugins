.pragma library

var COLORS = [
    {
        id: "yellow",
        label: "Yellow",
        light: {paper: "#fdf2c4", header: "#f5e299", border: "#dec974", ink: "#2b240d", placeholder: "#72653a", swatch: "#d9b342"},
        dark: {paper: "#332b18", header: "#3f351d", border: "#5c4d29", ink: "#f4ebd1", placeholder: "#b2a47d", swatch: "#d5b55c"}
    },
    {
        id: "green",
        label: "Green",
        light: {paper: "#dcf2df", header: "#c2e5c7", border: "#9ac9a1", ink: "#132b18", placeholder: "#4a6b51", swatch: "#4ca363"},
        dark: {paper: "#1b2e22", header: "#22392b", border: "#345640", ink: "#dcf0e2", placeholder: "#89aa94", swatch: "#6ebc88"}
    },
    {
        id: "blue",
        label: "Blue",
        light: {paper: "#dceafa", header: "#c1dcf5", border: "#97bee3", ink: "#132538", placeholder: "#4b647d", swatch: "#4d8ac7"},
        dark: {paper: "#1a2838", header: "#213246", border: "#334d6b", ink: "#dce9f7", placeholder: "#8ba3bd", swatch: "#74a8dc"}
    },
    {
        id: "pink",
        label: "Pink",
        light: {paper: "#fae0e6", header: "#f4c5d0", border: "#dfa3b1", ink: "#36141e", placeholder: "#7a4c58", swatch: "#c9627b"},
        dark: {paper: "#341d26", header: "#41242f", border: "#633748", ink: "#f7dfe7", placeholder: "#b88c9b", swatch: "#db869a"}
    },
    {
        id: "purple",
        label: "Purple",
        light: {paper: "#ebe1fa", header: "#d9c8f4", border: "#b8a2de", ink: "#231638", placeholder: "#62507c", swatch: "#8462c4"},
        dark: {paper: "#281f38", header: "#322746", border: "#4c3c6b", ink: "#eae1fa", placeholder: "#a193bd", swatch: "#a58ad9"}
    }
];

function normalizeColor(id) {
    if (id === "theme") return "theme";
    return COLORS.some(choice => choice.id === id) ? id : "yellow";
}

function softPalette(id, lightTheme) {
    const entry = COLORS.find(choice => choice.id === id) || COLORS[0];
    return lightTheme ? entry.light : entry.dark;
}

if (typeof module !== "undefined") module.exports = {COLORS: COLORS, normalizeColor: normalizeColor, softPalette: softPalette};
