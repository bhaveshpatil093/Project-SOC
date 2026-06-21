module.exports = {
    extends: ["react-app", "react-app/jest", "plugin:react-hooks/recommended"],
    rules: {
        "no-unused-vars": "warn",
        "react-hooks/exhaustive-deps": "warn",
        "no-console": ["warn", {allow: ["warn", "error"]}],
    }
}
