export const extensions = {
  all: [],
  getExtension: () => undefined,
};

export const initialize = () => undefined;

export const ILogService = Symbol("ILogService");

export const StandaloneServices = {
  initialize: () => undefined,
};

export const workspace = {
  getConfiguration: () => ({
    get: () => undefined,
  }),
};

export const window = {
  showInformationMessage: () => undefined,
  showWarningMessage: () => undefined,
  showErrorMessage: () => undefined,
};

export const commands = {
  registerCommand: () => ({
    dispose: () => undefined,
  }),
};

export const Uri = {
  parse: (value: string) => ({ toString: () => value }),
  file: (value: string) => ({ toString: () => value }),
};

export class EventEmitter<T> {
  event = () => undefined;

  fire(_: T) {
    return undefined;
  }
}
