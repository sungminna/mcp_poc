const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set(["favicon.png"]),
	mimeTypes: {".png":"image/png"},
	_: {
		client: {start:"_app/immutable/entry/start.iBduaIir.js",app:"_app/immutable/entry/app.CTBgxfVv.js",imports:["_app/immutable/entry/start.iBduaIir.js","_app/immutable/chunks/DwouiATX.js","_app/immutable/chunks/DCkLJiGP.js","_app/immutable/chunks/DzGvXcqd.js","_app/immutable/entry/app.CTBgxfVv.js","_app/immutable/chunks/DCkLJiGP.js","_app/immutable/chunks/DeRr3rea.js","_app/immutable/chunks/DV0htR0b.js","_app/immutable/chunks/Bug4azAl.js","_app/immutable/chunks/DoXvTXvK.js","_app/immutable/chunks/BC_43_Lu.js","_app/immutable/chunks/DzGvXcqd.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./chunks/0-tG6BwhH1.js')),
			__memo(() => import('./chunks/1-D-dY4wWa.js')),
			__memo(() => import('./chunks/2-BKLCKgAu.js')),
			__memo(() => import('./chunks/3-DjsntpwW.js')),
			__memo(() => import('./chunks/4-CNa5qEB8.js'))
		],
		routes: [
			{
				id: "/",
				pattern: /^\/$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 2 },
				endpoint: null
			},
			{
				id: "/login",
				pattern: /^\/login\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 3 },
				endpoint: null
			},
			{
				id: "/signup",
				pattern: /^\/signup\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 4 },
				endpoint: null
			}
		],
		prerendered_routes: new Set([]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();

const prerendered = new Set([]);

const base = "";

export { base, manifest, prerendered };
//# sourceMappingURL=manifest.js.map
