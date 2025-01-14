import { take, fork, put, takeEvery, call, all, cancelled, cancel, race, delay } from 'redux-saga/effects'
import { schema, arrayOf, normalize } from 'normalizr';
import {handleError} from "../utils";

import { userSchema } from '../schemas'


import {
  UPDATE_USER_LIST,

  LOAD_USER_REQUEST,
  LOAD_USER_SUCCESS,
  LOAD_USER_FAILURE,

  EDIT_USER_REQUEST,
  EDIT_USER_SUCCESS,
  EDIT_USER_FAILURE,

  CREATE_USER_REQUEST,
  CREATE_USER_SUCCESS,
  CREATE_USER_FAILURE
} from '../reducers/userReducer.js';

import { loadUserAPI, editUserAPI, createUserAPI } from "../api/userAPI";
import {ADD_FLASH_MESSAGE} from "../reducers/messageReducer";

function* updateStateFromUser(data) {
  //Schema expects a list of credit transfer objects
  if (data.users) {
    var user_list = data.users
  } else {
    user_list = [data.user]
  }

  const normalizedData = normalize(user_list, userSchema);

  const users = normalizedData.entities.users;

  yield put({type: UPDATE_USER_LIST, users});
}

// Load User Saga
function* loadUser({ payload }) {
  try {
    const load_result = yield call(loadUserAPI, payload);

    yield call(updateStateFromUser, load_result.data);

    const users = normalize(load_result.data, userSchema).entities.users;
    yield put({type: LOAD_USER_SUCCESS, users})

  } catch (fetch_error) {

    const error = yield call(handleError, fetch_error);

    yield put({type: LOAD_USER_FAILURE, error: error})
  }
}

function* watchLoadUser() {
  yield takeEvery(LOAD_USER_REQUEST, loadUser);
}


// Edit User Saga
function* editUser({ payload }) {
  try {
    const edit_response = yield call(editUserAPI, payload);

    yield call(updateStateFromUser, edit_response.data);

    yield put({type: EDIT_USER_SUCCESS, edit_user: edit_response});

    yield put({type: ADD_FLASH_MESSAGE, error: false, message: edit_response.message});

  } catch (fetch_error) {

    const error = yield call(handleError, fetch_error);

    yield put({type: EDIT_USER_FAILURE, error: error});

    yield put({type: ADD_FLASH_MESSAGE, error: true, message: error.message});
  }
}

function* watchEditUser() {
  yield takeEvery(EDIT_USER_REQUEST, editUser);
}

function* createUser({ payload }) {
  try {
    const result = yield call(createUserAPI, payload);

    yield call(updateStateFromUser, result.data);

    yield put({type: CREATE_USER_SUCCESS, result});

  } catch (fetch_error) {

    const error = yield call(handleError, fetch_error);

    yield put({type: CREATE_USER_FAILURE, error: error.message})
  }
}

function* watchCreateUser() {
  yield takeEvery(CREATE_USER_REQUEST, createUser);
}

export default function* userSagas() {
  yield all([
    watchLoadUser(),
    watchEditUser(),
    watchCreateUser()
  ])
}