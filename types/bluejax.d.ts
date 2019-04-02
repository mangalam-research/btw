import * as Promise from "bluebird";

export type AjaxCall = (...params: any[]) => Promise<any>;
export type $AjaxCall = (...params: any[]) => {
  promise: Promise<any>;
  xhr: JQueryXHR;
};

export function ajax(...params: any[]): Promise<any>;
export function make(options: any): $AjaxCall;
export function make(options: any, field: "promise"): AjaxCall;

export class HttpError extends Error {
  readonly jqXHR: jQuery.jqXHR;
}
