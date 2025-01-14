import React from 'react';
import { connect } from 'react-redux';
import styled from 'styled-components';
import QRCode from 'qrcode.react'

import AsyncButton from './../AsyncButton.jsx'

import {validateTFA, validateTFARequest} from '../../reducers/authReducer'

import { Input, StyledButton, ErrorMessage } from './../styledElements'

const mapStateToProps = (state) => {
  return {
    loginState: state.login,
    validateState: state.validateTFA
  };
};

const mapDispatchToProps = (dispatch) => {
  return {
    validateTFARequest: (otp, otp_expiry_interval) => dispatch(validateTFARequest({otp, otp_expiry_interval})),
  };
};

export class TFAValidator extends React.Component {
  constructor() {
    super();
    this.state = {
      otp: '',
      rememberComputer: false,
      errorMessage: ''
    };
  }

  componentWillReceiveProps(nextProps) {
    this.setState({errorMessage: (nextProps.validateState.error)})
  }

  attemptValidate() {
    if (this.state.otp === '') {
      this.setState({errorMessage: 'Please Enter a Validation Code'});
      return
    }
    if (this.state.otp.length < 6) {
      this.setState({errorMessage: 'Validation Code is 6 digits long'});
      return
    }

    this.props.validateTFARequest(this.state.otp, this.state.rememberComputer? 9999: 1)
  }

  onCodeKeyPress(e) {
    var otp = e.target.value;
    if (otp.length < 7) {
      this.setState({otp: otp, errorMessage: ''});
    }
  }

  onKeyup(e) {
    if (e.nativeEvent.keyCode != 13) return;
    this.attemptValidate()
  }

  onCheck(){
    this.setState({rememberComputer: !this.state.rememberComputer})
  }

  onClick(){
    this.attemptValidate()
  }

  render() {

    if (this.props.validateState.success) {
      return (
        <div style={{display: 'block', margin: '2em'}}>
          Two-step authentication successfully set up!
        </div>
      )
    }

    return(
    <div style={{display: 'block'}}>

      <Input type="text"
             value={this.state.otp}
             onChange={(e) => this.onCodeKeyPress(e)}
             onKeyUp={(e) => this.onKeyup(e)}
             placeholder="Your Code"
      />

      <label style={{marginLeft: '0.5em'}}>

        <input
              name="remember"
              type="checkbox"
              checked={this.state.rememberComputer}
              onChange={() => this.onCheck()}
        />
          Remember computer
      </label>

      <AsyncButton
        onClick={() => this.onClick()}
         isLoading={this.props.validateState.isRequesting}
         buttonStyle={{width: 'calc(100% - 1em)', display: 'flex'}}
         buttonText="Verify"
      />

      <div style={{textAlign: 'center'}}>
        Enter the 6-digit code you see in the app.
      </div>

      <ErrorMessage>
        {this.state.errorMessage}
      </ErrorMessage>
    </div>

  );
  }
};


export default connect(mapStateToProps, mapDispatchToProps)(TFAValidator);

