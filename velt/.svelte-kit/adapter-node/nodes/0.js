

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_layout.svelte.js')).default;
export const imports = ["_app/immutable/nodes/0.TnrZFciV.js","_app/immutable/chunks/DV0htR0b.js","_app/immutable/chunks/DCkLJiGP.js"];
export const stylesheets = ["_app/immutable/assets/0.CgNu35-Q.css"];
export const fonts = [];
