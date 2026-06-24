// Loads every book-study data file. Drop a new JSON into src/data/books/ and it
// shows up on the shelf and gets its own /<slug>/ page automatically.
const modules = import.meta.glob('../data/books/*.json', { eager: true });

export const books = Object.values(modules)
  .map((m) => m.default)
  .sort((a, b) => (a.order ?? 99) - (b.order ?? 99));

export const getBook = (slug) => books.find((b) => b.slug === slug);
