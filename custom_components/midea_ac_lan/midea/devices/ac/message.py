import logging
from enum import IntEnum
from ...core.message import (
    MessageType,
    NewProtocolParamPack,
    MessageRequest,
    MessageResponse,
    MessageBody,
)

_LOGGER = logging.getLogger(__name__)


class NewProtocolParams(IntEnum):
    indoor_humidity = 0x15        # 2126
    breezyless = 0x18             # 1975
    prompt_tone = 0x1A
    indirect_wind = 0x42


class MessageQuery(MessageRequest):
    def __init__(self):
        super().__init__(
            device_type=0xAC,
            message_type=MessageType.query,
            body_type=0x41)

    @property
    def _body(self):
        return bytearray([
            0x81, 0x00, 0xFF, 0x03,
            0xFF, 0x00,
            # 0x02 - Indoor Temperature; 0x03 - Outdoor Temperature
            0x02,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00
        ])


class MessagePowerQuery(MessageRequest):
    def __init__(self):
        super().__init__(
            device_type=0xAC,
            message_type=MessageType.query,
            body_type=0x41)

    @property
    def _body(self):
        return bytearray([
            0x21, 0x01, 0x40, 0x00, 0x01
            # 0x21, 0x01, 0x44, 0x00, 0x01
        ])


class MessageSwitchDisplay(MessageRequest):
    def __init__(self):
        super().__init__(
            device_type=0xAC,
            message_type=MessageType.query,
            body_type=0x41)

    @property
    def _body(self):
        return bytearray([
            0x81, 0x00, 0xFF, 0x02,
            0xFF, 0x02, 0x02,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00
        ])


class MessageNewProtocolQuery(MessageRequest):
    def __init__(self):
        super().__init__(
            device_type=0xAC,
            message_type=MessageType.query,
            body_type=0xB1)

    @property
    def _body(self):
        query_params = [
            NewProtocolParams.indirect_wind,
            NewProtocolParams.breezyless,
            NewProtocolParams.indoor_humidity
        ]

        _body = bytearray([len(query_params)])
        for param in query_params:
            _body.extend(bytearray([param & 0xFF, param >> 8]))
        return _body


class MessageGeneralSet(MessageRequest):
    def __init__(self):
        super().__init__(
            device_type=0xAC,
            message_type=MessageType.set,
            body_type=0x40)
        self.power = False
        self.prompt_tone = True
        self.mode = 0
        self.target_temperature = 20.0
        self.fan_speed = 102
        self.swing_vertical = False
        self.swing_horizontal = False
        self.turbo_mode = False
        self.smart_eye = False
        self.dry = False
        self.aux_heat = False
        self.eco_mode = False
        self.temp_fahrenheit = False
        self.night_light = False
        self.natural_wind = False
        self.comfort_mode = False

    @property
    def _body(self):
        # Byte1, Power, prompt_tone
        power = 0x01 if self.power else 0
        prompt_tone = 0x40 if self.prompt_tone else 0
        # Byte2, mode target_temperature
        mode = (self.mode << 5) & 0xe0
        target_temperature = (int(self.target_temperature) & 0xf) | \
                             (0x10 if int(round(self.target_temperature * 2)) % 2 != 0 else 0)
        # Byte 3, fan_speed
        fan_speed = self.fan_speed & 0x7f
        # Byte 7, swing_mode
        swing_mode = 0x30 | \
                     (0x0c if self.swing_vertical else 0) | \
                     (0x03 if self.swing_horizontal else 0)
        # Byte 8, turbo
        turbo_mode = 0x20 if self.turbo_mode else 0
        # Byte 9 aux_heat eco_mode
        smart_eye = 0x01 if self.smart_eye else 0
        dry = 0x04 if self.dry else 0
        aux_heat = 0x08 if self.aux_heat else 0
        eco_mode = 0x80 if self.eco_mode else 0
        # Byte 10 temp_fahrenheit
        temp_fahrenheit = 0x04 if self.temp_fahrenheit else 0
        night_light = 0x10 if self.night_light else 0
        # Byte 17 natural_wind
        natural_wind = 0x40 if self.natural_wind else 0
        # Byte 22 comfort_mode
        comfort_mode = 0x01 if self.comfort_mode else 0

        return bytearray([
            power | prompt_tone,
            mode | target_temperature,
            fan_speed,
            0x00, 0x00, 0x00,
            swing_mode,
            turbo_mode,
            smart_eye | dry | aux_heat | eco_mode,
            temp_fahrenheit | night_light,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00,
            natural_wind,
            0x00, 0x00, 0x00, 0x00,
            comfort_mode
        ])


class MessageNewProtocolSet(MessageRequest):
    def __init__(self):
        super().__init__(
            device_type=0xAC,
            message_type=MessageType.set,
            body_type=0xB0)
        self.indirect_wind = None
        self.prompt_tone = None
        self.breezyless = None

    @property
    def _body(self):
        pack_count = 0
        payload = bytearray([0x00])
        if self.breezyless is not None:
            pack_count += 1
            payload.extend(
                NewProtocolParamPack.pack(
                    param=NewProtocolParams.breezyless,
                    value=bytearray([0x01 if self.breezyless else 0x00])
                ))
        if self.indirect_wind is not None:
            pack_count += 1
            payload.extend(
                NewProtocolParamPack.pack(
                    param=NewProtocolParams.indirect_wind,
                    value=bytearray([0x02 if self.indirect_wind else 0x01])
                ))
        if self.prompt_tone is not None:
            pack_count += 1
            payload.extend(
                NewProtocolParamPack.pack(
                    param=NewProtocolParams.prompt_tone,
                    value=bytearray([0x01 if self.prompt_tone else 0x00])
            ))
        payload[0] = pack_count
        return payload


class XA0MessageBody(MessageBody):
    def __init__(self, body):
        super().__init__(body)
        self.power = (body[1] & 0x1) > 0
        self.target_temperature = ((body[1] & 0x3E) >> 1) - 4 + 16.0 + (0.5 if body[1] & 0x40 > 0 else 0.0)
        self.mode = (body[2] & 0xe0) >> 5
        self.fan_speed = body[3] & 0x7f
        self.swing_vertical = (body[7] & 0xC) > 0
        self.swing_horizontal = (body[7] & 0x3) > 0
        self.turbo_mode = (body[8] & 0x20) > 0
        self.smart_eye = (body[9] & 0x01) > 0
        self.dry = (body[9] & 0x04) > 0
        self.aux_heat = (body[9] & 0x08) > 0
        self.eco_mode = (body[9] & 0x10) > 0
        self.night_light = (body[10] & 0x10) > 0
        self.natural_wind = (body[10] & 0x40) > 0
        self.screen_display = (body[11] & 0x7 != 0x7)
        self.comfort_mode = (body[14] & 0x1) > 0


class XA1MessageBody(MessageBody):
    def __init__(self, body):
        super().__init__(body)
        TempInteger = int((body[13] - 50) / 2)
        TemperatureDot = (body[18] & 0xF) * 0.1 if len(body) > 18 else 0
        if body[13] > 49:
            self.indoor_temperature = TempInteger + TemperatureDot
        else:
            self.indoor_temperature = TempInteger - TemperatureDot
        if body[14] == 0xFF:
            self.outdoor_temperature = 0.0
        else:
            TempInteger = int((body[14] - 50) / 2)
            TemperatureDot = ((body[18] & 0xF0) >> 4) * 0.1 if len(body) > 18 else 0
            if body[14] > 49:
                self.outdoor_temperature = TempInteger + TemperatureDot
            else:
                self.outdoor_temperature = TempInteger - TemperatureDot
        self.indoor_humidity = body[17]


class XBXMessageBody(MessageBody):
    def __init__(self, body, bt):
        super().__init__(body)
        if bt == 0xb5:
            pack_len = 4
        else:
            pack_len = 5
        params = NewProtocolParamPack.parse(body[1:-1], pack_len=pack_len)
        if NewProtocolParams.indirect_wind in params:
            self.indirect_wind = (params[NewProtocolParams.indirect_wind][0] == 0x02)
        if NewProtocolParams.indoor_humidity in params:
            self.indoor_humidity = params[NewProtocolParams.indoor_humidity][0]
        if NewProtocolParams.breezyless in params:
            self.breezyless = params[NewProtocolParams.breezyless][0] / 1.0


class XC0MessageBody(MessageBody):
    def __init__(self, body):
        super().__init__(body)
        self.power = (body[1] & 0x1) > 0
        self.mode = (body[2] & 0xe0) >> 5
        self.target_temperature = (body[2] & 0xf) + 16.0 + (0.5 if body[0x02] & 0x10 > 0 else 0.0)
        self.fan_speed = body[3] & 0x7f
        self.swing_vertical = (body[7] & 0xC) > 0
        self.swing_horizontal = (body[7] & 0x3) > 0
        self.turbo_mode = (body[8] & 0x20) > 0
        self.smart_eye = (body[8] & 0x40) > 0
        self.natural_wind = (body[9] & 0x2) > 0
        self.dry = (body[9] & 0x4) > 0
        self.eco_mode = (body[9] & 0x10) > 0
        self.aux_heat = (body[9] & 0x08) > 0
        self.temp_fahrenheit = (body[10] & 0x04) > 0
        self.night_light = (body[10] & 0x10) > 0
        TempInteger = int((body[11] - 50) / 2)
        TemperatureDot = (body[15] & 0xF) * 0.1
        if body[11] > 49:
            self.indoor_temperature = TempInteger + TemperatureDot
        else:
            self.indoor_temperature = TempInteger - TemperatureDot
        if body[12] == 0xFF:
            self.outdoor_temperature = 0.0
        else:
            TempInteger = int((body[12] - 50) / 2)
            TemperatureDot = ((body[15] & 0xF0) >> 4) * 0.1
            if body[12] > 49:
                self.outdoor_temperature = TempInteger + TemperatureDot
            else:
                self.outdoor_temperature = TempInteger - TemperatureDot
        self.screen_display = (body[14] & 0x70 != 0x70)
        self.comfort_mode = (body[22] & 0x1) > 0 if len(body) > 22 else False


class MessageACResponse(MessageResponse):
    def __init__(self, message):
        super().__init__(message)
        body = message[10: -2]
        if self._body_type == 0xA0:
            self._body = XA0MessageBody(body)
            self.power = self._body.power
            self.target_temperature = self._body.target_temperature
            self.mode = self._body.mode
            self.fan_speed = self._body.fan_speed
            self.swing_vertical = self._body.swing_vertical
            self.swing_horizontal = self._body.swing_horizontal
            self.turbo_mode = self._body.turbo_mode
            self.smart_eye = self._body.smart_eye
            self.dry = self._body.dry
            self.aux_heat = self._body.aux_heat
            self.eco_mode = self._body.eco_mode
            self.night_light = self._body.night_light
            self.natural_wind = self._body.natural_wind
            self.screen_display = self._body.screen_display
            self.comfort_mode = self._body.comfort_mode
        elif self._body_type == 0xA1:
            self._body = XA1MessageBody(body)
            self.indoor_temperature = self._body.indoor_temperature
            self.outdoor_temperature = self._body.outdoor_temperature
            self.indoor_humidity = self._body.indoor_humidity
        elif self._body_type == 0xB0 or self._body_type == 0xB1 or self._body_type == 0xB5:
            self._body = XBXMessageBody(body, self._body_type)
            if hasattr(self._body, "indirect_wind"):
                self.indirect_wind = self._body.indirect_wind
            if hasattr(self._body, "indoor_humidity"):
                self.indoor_humidity = self._body.indoor_humidity
            if hasattr(self._body, "breezyless"):
                self.breezyless = self._body.breezyless
        elif self._body_type == 0xC0:
            self._body = XC0MessageBody(body)
            self.power = self._body.power
            self.mode = self._body.mode
            self.target_temperature = self._body.target_temperature
            self.fan_speed = self._body.fan_speed
            self.swing_vertical = self._body.swing_vertical
            self.swing_horizontal = self._body.swing_horizontal
            self.turbo_mode = self._body.turbo_mode
            self.smart_eye = self._body.smart_eye
            self.natural_wind = self._body.natural_wind
            self.dry = self._body.dry
            self.aux_heat = self._body.aux_heat
            self.eco_mode = self._body.eco_mode
            self.temp_fahrenheit = self._body.temp_fahrenheit
            self.night_light = self._body.night_light
            self.indoor_temperature = self._body.indoor_temperature
            self.outdoor_temperature = self._body.outdoor_temperature
            self.screen_display = self._body.screen_display
            self.comfort_mode = self._body.comfort_mode
        else:
            self._body = MessageBody(body)