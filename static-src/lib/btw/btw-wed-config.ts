/* tslint:disable: no-any no-reserved-keywords */
declare var require: any;
export const config: any = {
  schema: require.toUrl("btw/btw-storage.js"),
  mode: {
    path: "btw/btw-mode",
    options: {
      bibl_url: "/rest/bibliography/all",
    },
  },
};
