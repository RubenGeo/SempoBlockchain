import React from 'react';
import { connect } from 'react-redux';
import ReactPasswordStrength from 'react-password-strength';

import { registerRequest } from '../../reducers/authReducer'

import AsyncButton from './../AsyncButton.jsx'

import { Input, ErrorMessage } from './../styledElements'

const mapStateToProps = (state) => {
  return {
    register_status: state.register
  };
};

const mapDispatchToProps = (dispatch) => {
  return {
    registerRequest: (payload) => dispatch(registerRequest(payload)),
  };
};

class RegisterFormContainer extends React.Component {
  constructor() {
    super();
    this.state = {
      username: '',
      password: '',
      reenter_password: '',
      passwordIsValid: false,
      user_missing: false,
      invalid_username: false,
      password_missing: false,
      password_missmatch: false,
      invalid_register: false,
      password_invalid: false,
      invite: false,
    };
  }

  componentWillMount() {
    if (this.props.email != null) {
      this.setState({username: this.props.email, invite: true})
    }
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.email != null) {
      this.setState({username: nextProps.email, invite: true})
    }
    this.setState({invalid_register: (nextProps.register_status.error)})

  }

  attemptregister() {

    var invalid_email = (this.state.username.match(/^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$/) == null);

    if (this.state.username === '') {
      this.setState({user_missing: true});
      return
    }
    if (invalid_email) {
      this.setState({invalid_username: true});
      return
    }

    if (this.state.password === '') {
      this.setState({password_missing: true});
      return
    }

    if (!this.state.passwordIsValid) {
      this.setState({password_invalid: true});
      return
    }

    if (this.state.password !== this.state.reenter_password) {
      this.setState({password_missmatch: true});
      return
    }

    this.props.registerRequest({username: this.state.username, password: this.state.password})
  }

  onUserFieldKeyPress(e) {
    var username = e.target.value;
    this.setState({username: username, user_missing: false});
    if (e.nativeEvent.keyCode != 13) return;
    this.attemptregister()
  }

  onPasswordFieldKeyPress(e) {
    var password = e.password;
    var isValid = e.isValid;
    this.setState({password: password, password_missing: false, passwordIsValid: isValid});
  }

  onReenterPasswordFieldKeyPress(e) {
    var reenter_password = e.target.value;
    this.setState({reenter_password: reenter_password, password_missmatch: false});
    if (e.nativeEvent.keyCode != 13) return;
    this.attemptregister()
  }

  onClick(){
    this.attemptregister()
  }


  render() {
    if (this.props.register_status.registerSuccess) {
      return (
        <div>
          <h3> Register Success </h3>
          <div> We've sent you an activation email</div>
        </div>
      )
    }

    return (
      <RegisterForm
        onUserFieldKeyPress = {(e) => this.onUserFieldKeyPress(e)}
        onPasswordFieldKeyPress = {(e) => this.onPasswordFieldKeyPress(e)}
        onReenterPasswordFieldKeyPress = {(e) => this.onReenterPasswordFieldKeyPress(e)}
        onClick = {() => this.onClick()}
        user_missing = {this.state.user_missing}
        invalid_username = {this.state.invalid_username}
        password_missing = {this.state.password_missing}
        password_missmatch = {this.state.password_missmatch}
        password_invalid = {this.state.password_invalid}
        invalid_register = {this.state.invalid_register}
        isRegistering = {this.props.register_status.isRegistering}
        state={this.state}
      />
    )
  }
}

const RegisterForm = function(props) {


  if (props.user_missing) {
    var error_message = 'Email Missing'
  } else if (props.invalid_username) {
    error_message = 'Invalid Email'
  } else if (props.password_missing) {
    error_message = 'Password Missing'
  } else if (props.password_missmatch) {
    error_message = 'Passwords do not match'
  } else if (props.invalid_register) {
    error_message = props.invalid_register
  } else if (props.password_invalid) {
    error_message = 'Password too weak'
  } else {
    error_message = ''
  }

  return(
    <div>

      <div style={{display: 'block'}}>

        <ErrorMessage>
          {error_message}
        </ErrorMessage>

        <p style={props.state.invite ? { margin: '1em 0.5em', textAlign: 'center' } : { display: 'none' }}>{props.state.username}</p>

        <Input type="email"
               onKeyUp={props.onUserFieldKeyPress}
               placeholder="Email"
               style={props.state.invite ? { display: 'none' } : null}
        />

        <ReactPasswordStrength
          minLength={6}
          type="password"
          changeCallback={data => props.onPasswordFieldKeyPress(data)}
          inputProps={{ placeholder: 'Password'}}
          className={'default-input'}
        />

        <Input type="password"
                 onKeyUp={props.onReenterPasswordFieldKeyPress}
                 placeholder="Retype Passwords"
          />

      </div>

        <AsyncButton onClick={props.onClick} isLoading={props.isRegistering} buttonStyle={{width: 'calc(100% - 1em)', display: 'flex'}} buttonText="REGISTER"/>

    </div>
  );

};export default connect(mapStateToProps, mapDispatchToProps)(RegisterFormContainer);

