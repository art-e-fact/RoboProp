/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./node_modules/flowbite/**/*.js"
  ],
  theme: {
    extend: {},
    colors: {
      "action": "#5B4CA9"
    }
  },
  plugins: [
    require("flowbite/plugin")
  ],
}

