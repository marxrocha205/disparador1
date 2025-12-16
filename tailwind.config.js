/** @type {import('tailwindcss').Config} */
module.exports = {
  purge: [
      './**/templates/*.html',
  ],
  theme: {
      extend: {
        colors: {
          primary: '#1e4b8f', // Define a cor personalizada
        },
      },
  },
  plugins: [],
}
