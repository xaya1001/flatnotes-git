// client/git-integration/events.js
export const GIT_OPERATION = {
  WILL_START: "git:operation:will-start",
  DID_SUCCEED: "git:operation:did-succeed",
  DID_FAIL: "git:operation:did-fail",
};

export const GIT_CONFLICT = {
  DETECTED: "git:conflict:detected",
};
