import { call, fork, put, take, all, cancelled, cancel, takeEvery } from 'redux-saga/effects';

import {handleError, removeSessionToken, storeSessionToken, storeTFAToken} from '../utils'

import {
  requestApiToken,
  refreshApiToken,
  registerAPI,
  activateAPI,
  authenticatePusher,
  requestResetEmailAPI,
  ResetPasswordAPI,
  getUserList,
  updateUserAPI,
  inviteUserAPI,
  ValidateTFAAPI
} from '../api/authApi'

import {
  REAUTH_REQUEST,
  LOGIN_REQUEST,
  LOGIN_SUCCESS,
  LOGIN_PARTIAL,
  LOGIN_FAILURE,
  LOGOUT,
  loginFailure,
  loginSuccess,
  REGISTER_REQUEST,
  REGISTER_SUCCESS,
  REGISTER_FAILURE,
  registerSuccess,
  registerFailure,
  ACTIVATE_REQUEST,
  ACTIVATE_SUCCESS,
  ACTIVATE_FAILURE,
  REQUEST_RESET_REQUEST,
  REQUEST_RESET_SUCCESS,
  REQUEST_RESET_FAILURE,
  RESET_PASSWORD_REQUEST,
  RESET_PASSWORD_SUCCESS,
  RESET_PASSWORD_FAILURE,
  USER_LIST_REQUEST,
  USER_LIST_SUCCESS,
  USER_LIST_FAILURE,
  UPDATE_USER_REQUEST,
  UPDATE_USER_SUCCESS,
  UPDATE_USER_FAILURE,
  INVITE_USER_REQUEST,
  INVITE_USER_SUCCESS,
  INVITE_USER_FAILURE,
  VALIDATE_TFA_REQUEST,
  VALIDATE_TFA_SUCCESS,
  VALIDATE_TFA_FAILURE
} from '../reducers/authReducer';

import {browserHistory} from "../app.jsx";
import {ADD_FLASH_MESSAGE} from "../reducers/messageReducer";

export function* logout() {
    yield call(removeSessionToken)
}

function createLoginSuccessObject(token) {
  return {
    type: LOGIN_SUCCESS,
    token: token.auth_token,
    userId: token.user_id,
    vendorId: token.vendor_id,
    email: token.email,
    adminTier: token.admin_tier,
    usdToSatoshiRate: token.usd_to_satoshi_rate
  }
}

function* requestToken({username, password}) {
  try {
    const token_response = yield call(requestApiToken, username, password);

    console.log("token response is", token_response)

    if (token_response.status === 'success') {
      yield put(createLoginSuccessObject(token_response));
      yield call(storeSessionToken, token_response.auth_token );
      yield call (authenticatePusher);
      return token_response

    } else if (token_response.tfa_url) {
      yield call(storeSessionToken, token_response.auth_token );
      yield put({
        type: LOGIN_PARTIAL,
        error: token_response.message,
        tfaURL: token_response.tfa_url,
        tfaFailure: true
      });

      return token_response
    } else if (token_response.tfa_failure) {
      yield call(storeSessionToken, token_response.auth_token );
      yield put({
        type: LOGIN_PARTIAL,
        error: token_response.message,
        tfaURL: null,
        tfaFailure: true});
      return token_response
    } else {
      yield put({type: LOGIN_FAILURE, error: token_response.message})
    }

  } catch(error) {
    yield put({type: LOGIN_FAILURE, error: error.statusText})
  } finally {
    if (yield cancelled()) {
      // ... put special cancellation handling code here
    }
  }
}

function* watchLoginRequest() {
  var reauth = yield call(refreshToken);
  yield takeEvery(LOGIN_REQUEST, requestToken);
}

function* refreshToken() {
  try {
    yield put({type: REAUTH_REQUEST});
    const token_request = yield call(refreshApiToken);
    if (token_request.auth_token) {
      yield put(createLoginSuccessObject(token_request));
      yield call(storeSessionToken, token_request.auth_token );
      yield call (authenticatePusher);
    }
    return token_request
  } catch(error) {
    yield put({type: LOGOUT});
    yield call(removeSessionToken);
    return error
  } finally {
    if (yield cancelled()) {
      // ... put special cancellation handling code here
    }
  }
}

function* watchLogoutRequest() {
  const action = yield takeEvery([LOGOUT, LOGIN_FAILURE], logout);
}


// Create Account Saga
function* register({ username, password }) {
  try {
    const registered_account = yield call(registerAPI, username, password);
    if (registered_account.status === 'success') {
      yield put({type: REGISTER_SUCCESS, registered_account});
    } else {
      yield put({type: REGISTER_FAILURE, error: registered_account.message})
    }
  } catch (error) {
    yield put({type: REGISTER_FAILURE, error: error.statusText})
  }
}

function* watchRegisterRequest() {
  yield takeEvery(REGISTER_REQUEST, register);
}

function* activate({activation_token}) {
  try {
    const activated_account = yield call(activateAPI, activation_token);
    yield put({type: ACTIVATE_SUCCESS, activated_account});
    yield put(createLoginSuccessObject(activated_account));
    yield call(storeSessionToken, activated_account.auth_token );
  } catch (error) {
    yield put({type: ACTIVATE_FAILURE, error: error.statusText})
  }
}

function* watchActivateRequest() {
  yield takeEvery(ACTIVATE_REQUEST, activate);
}

function* resetEmailRequest({email}) {
  try {
    const resetEmailResponse = yield call(requestResetEmailAPI, email);
    yield put({type: REQUEST_RESET_SUCCESS, resetEmailResponse});
  } catch (error) {
    yield put({type: REQUEST_RESET_FAILURE, error: error.statusText})
  }
}

function* watchResetEmailRequest() {
  yield takeEvery(REQUEST_RESET_REQUEST, resetEmailRequest);
}

function* resetPassword({payload}) {
  try {
    const resetPasswordResponse = yield call(ResetPasswordAPI, payload);
    yield put({type: RESET_PASSWORD_SUCCESS, resetPasswordResponse});
    yield put({type: LOGOUT});
  } catch (error) {
    yield put({type: RESET_PASSWORD_FAILURE, error: error.statusText})
  }
}

function* watchResetPassword() {
  yield takeEvery(RESET_PASSWORD_REQUEST, resetPassword);
}

function* userList() {
  try {
    const load_result = yield call(getUserList);
    yield put({type: USER_LIST_SUCCESS, load_result});
  } catch (error) {
    yield put({type: USER_LIST_FAILURE, error: error.statusText})
  }
}

function* watchLoadUserList() {
  yield takeEvery(USER_LIST_REQUEST, userList);
}

function* updateUserRequest({payload}) {
    try {
        const result = yield call(updateUserAPI, payload);
        if (result.status === 'success') {
          yield put({type: UPDATE_USER_SUCCESS, result});
          const load_result = yield call(getUserList);
          yield put({type: USER_LIST_SUCCESS, load_result});
        } else {
          yield put({type: UPDATE_USER_FAILURE, error: result.message})
        }
    } catch (error) {
        yield put({type: UPDATE_USER_FAILURE, error: error})
    }
}

function* watchUpdateUserRequest() {
    yield takeEvery(UPDATE_USER_REQUEST, updateUserRequest);
}

function* inviteUserRequest({ payload }) {
    try {
      const result = yield call(inviteUserAPI, payload);
      yield put({type: INVITE_USER_SUCCESS, result});
      yield put({type: ADD_FLASH_MESSAGE, error: false, message: result.message});
      browserHistory.push('/settings')
    } catch (fetch_error) {
      const error = yield call(handleError, fetch_error);
      yield put({type: INVITE_USER_FAILURE, error: error.message})
    }
}

function* watchInviteUserRequest() {
    yield takeEvery(INVITE_USER_REQUEST, inviteUserRequest);
}


function* validateTFA({payload}) {
  try {
    const validateTFAresponse = yield call(ValidateTFAAPI, payload);

    yield put({type: VALIDATE_TFA_SUCCESS, validateTFAresponse});
    yield call(storeTFAToken, validateTFAresponse.tfa_auth_token );
    yield put(createLoginSuccessObject(validateTFAresponse));
    yield call (authenticatePusher);

    return validateTFAresponse

  } catch (error) {

    const response = yield call(handleError, error);

    yield put({type: VALIDATE_TFA_FAILURE, error: response.message})
  }
}

function* watchValidateTFA() {
  yield takeEvery(VALIDATE_TFA_REQUEST, validateTFA);
}


export default function* authSagas() {
  yield all([
    watchRegisterRequest(),
    watchLoginRequest(),
    watchLogoutRequest(),
    watchActivateRequest(),
    watchResetEmailRequest(),
    watchResetPassword(),
    watchLoadUserList(),
    watchUpdateUserRequest(),
    watchInviteUserRequest(),
    watchValidateTFA()
  ])
}