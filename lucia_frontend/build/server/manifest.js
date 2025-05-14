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
		client: {start:"_app/immutable/entry/start.B1MVqn5R.js",app:"_app/immutable/entry/app.CqQNAK_L.js",imports:["_app/immutable/entry/start.B1MVqn5R.js","_app/immutable/chunks/BDDU8JJk.js","_app/immutable/chunks/DCkLJiGP.js","_app/immutable/chunks/DzGvXcqd.js","_app/immutable/entry/app.CqQNAK_L.js","_app/immutable/chunks/DCkLJiGP.js","_app/immutable/chunks/DeRr3rea.js","_app/immutable/chunks/DV0htR0b.js","_app/immutable/chunks/Bug4azAl.js","_app/immutable/chunks/DoXvTXvK.js","_app/immutable/chunks/BC_43_Lu.js","_app/immutable/chunks/DzGvXcqd.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./chunks/0-9FSf7B1t.js')),
			__memo(() => import('./chunks/1-CEyRIaNB.js')),
			__memo(() => import('./chunks/2-HokvECu0.js')),
			__memo(() => import('./chunks/3-CDMgV0cT.js')),
			__memo(() => import('./chunks/4-DuDg2V3i.js'))
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
